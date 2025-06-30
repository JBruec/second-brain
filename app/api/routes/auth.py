from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.models.user import UserCreate, UserInDB, User, UserUpdate
from app.core.config import settings
from app.core.database import MongoDB

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get the current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    collection = MongoDB.get_collection("users")
    user_doc = await collection.find_one({"_id": user_id})
    if user_doc is None:
        raise credentials_exception
    
    return User(
        id=str(user_doc["_id"]),
        username=user_doc["username"],
        email=user_doc["email"],
        full_name=user_doc.get("full_name"),
        is_active=user_doc["is_active"],
        created_at=user_doc["created_at"],
        updated_at=user_doc["updated_at"]
    )

@router.post("/register", response_model=dict)
async def register(user: UserCreate):
    """Register a new user"""
    try:
        collection = MongoDB.get_collection("users")
        
        # Check if user already exists
        existing_user = await collection.find_one({
            "$or": [
                {"email": user.email},
                {"username": user.username}
            ]
        })
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or username already exists"
            )
        
        # Hash password and create user
        hashed_password = get_password_hash(user.password)
        user_doc = UserInDB(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            hashed_password=hashed_password
        )
        
        # Insert user
        result = await collection.insert_one(user_doc.dict(by_alias=True, exclude={"id"}))
        user_id = str(result.inserted_id)
        
        # Create access token
        access_token = create_access_token(data={"sub": user_id})
        
        logger.info(f"New user registered: {user.username}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "username": user.username
        }
        
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=dict)
async def login(username: str, password: str):
    """Login user"""
    try:
        collection = MongoDB.get_collection("users")
        
        # Find user by username or email
        user_doc = await collection.find_one({
            "$or": [
                {"username": username},
                {"email": username}
            ]
        })
        
        if not user_doc or not verify_password(password, user_doc["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user_doc["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user_doc["_id"])})
        
        logger.info(f"User logged in: {user_doc['username']}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": str(user_doc["_id"]),
            "username": user_doc["username"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user information"""
    try:
        collection = MongoDB.get_collection("users")
        
        # Prepare update data
        update_data = {}
        if user_update.username:
            # Check if username is already taken
            existing = await collection.find_one({
                "username": user_update.username,
                "_id": {"$ne": current_user.id}
            })
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            update_data["username"] = user_update.username
            
        if user_update.email:
            # Check if email is already taken
            existing = await collection.find_one({
                "email": user_update.email,
                "_id": {"$ne": current_user.id}
            })
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already taken"
                )
            update_data["email"] = user_update.email
            
        if user_update.full_name is not None:
            update_data["full_name"] = user_update.full_name
            
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            await collection.update_one(
                {"_id": current_user.id},
                {"$set": update_data}
            )
        
        # Return updated user
        updated_doc = await collection.find_one({"_id": current_user.id})
        return User(
            id=str(updated_doc["_id"]),
            username=updated_doc["username"],
            email=updated_doc["email"],
            full_name=updated_doc.get("full_name"),
            is_active=updated_doc["is_active"],
            created_at=updated_doc["created_at"],
            updated_at=updated_doc["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )