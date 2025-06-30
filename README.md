# AI Second Brain

A comprehensive AI-powered personal assistant that manages documents, projects, and integrates with the Apple ecosystem. Built with FastAPI, MongoDB, Mem0, and Voyage AI.

## Features

### 🧠 Smart Memory System
- **Entity Recognition**: Automatically extracts and tracks people, places, organizations from your content
- **Smart Storage**: Uses Mem0 for intelligent memory management and relationship building
- **Contextual Search**: Powered by Voyage AI embeddings for semantic search across all content

### 📁 Document Management
- **Multi-format Support**: Upload and process PDFs, Word docs, Excel files, PowerPoint, images, and more
- **Automatic Processing**: Text extraction and content analysis
- **Project Organization**: Group documents by projects with custom instructions

### 🗂️ Project Management
- **Project-specific Instructions**: AI behavior customization per project
- **Document Organization**: Link documents to projects
- **Activity Tracking**: Monitor project progress and activity

### 📅 Apple Ecosystem Integration
- **Calendar Sync**: Create and manage events in Apple Calendar
- **Reminders Integration**: Sync tasks with Apple Reminders
- **AppleScript Automation**: Native macOS integration

### 🔍 Unified Search
- **Cross-platform Search**: Search across documents, projects, events, reminders, and memories
- **Entity-based Search**: Find all information about specific people or organizations
- **Smart Suggestions**: Contextual search suggestions

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: MongoDB with Motor (async driver)
- **Memory Store**: Mem0 for intelligent memory management
- **Embeddings**: Voyage AI for semantic search and document understanding
- **LLM**: Abacus.ai for natural language processing
- **Apple Integration**: AppleScript for Calendar and Reminders
- **Deployment**: Railway-ready with Docker support

## Quick Start

### Prerequisites

- Python 3.11+
- MongoDB instance (local or cloud)
- API keys for Mem0, Voyage AI, and Abacus.ai

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd second-brain
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run the application**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### Environment Variables

```bash
# Required
MONGODB_URL=mongodb://localhost:27017
MEM0_API_KEY=your-mem0-api-key
VOYAGE_API_KEY=your-voyage-ai-api-key
ABACUS_API_KEY=your-abacus-ai-api-key

# Optional
SECRET_KEY=your-secret-key
UPLOAD_DIR=./uploads
APPLE_SCRIPT_ENABLED=true  # macOS only
```

## API Documentation

Once running, visit:
- **Interactive API docs**: `http://localhost:8000/docs`
- **ReDoc documentation**: `http://localhost:8000/redoc`

### Key Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user info

#### Projects
- `GET /api/projects/` - List projects
- `POST /api/projects/` - Create project
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

#### Documents
- `POST /api/documents/upload` - Upload file
- `POST /api/documents/` - Create text document
- `GET /api/documents/` - List documents
- `GET /api/documents/{id}` - Get document
- `PUT /api/documents/{id}` - Update document

#### Memory & Search
- `POST /api/memory/add` - Add memory
- `GET /api/memory/search` - Search memories
- `GET /api/memory/entity/{name}` - Get entity knowledge
- `GET /api/search/` - Unified search

#### Calendar & Reminders
- `POST /api/calendar/events` - Create calendar event
- `GET /api/calendar/events` - List events
- `POST /api/reminders/` - Create reminder
- `GET /api/reminders/` - List reminders

## Deployment

### Railway Deployment

1. **Connect your repository to Railway**
2. **Set environment variables in Railway dashboard**
3. **Deploy automatically on git push**

The `railway.json` file is already configured for optimal deployment.

### Docker Deployment

```bash
# Build image
docker build -t second-brain .

# Run container
docker run -p 8000:8000 --env-file .env second-brain
```

### MongoDB Atlas Setup

1. Create a MongoDB Atlas cluster
2. Get connection string
3. Set `MONGODB_URL` environment variable

## Apple Integration Setup (macOS)

1. **Enable AppleScript**
```bash
# Set environment variable
APPLE_SCRIPT_ENABLED=true
```

2. **Create Calendar and Reminders Lists**
- Create "Second Brain" calendar in Apple Calendar
- Create "Second Brain" list in Apple Reminders

3. **Grant Permissions**
- Allow terminal/app to control Calendar and Reminders when prompted

## Development

### Project Structure
```
second-brain/
├── app/
│   ├── api/routes/          # API endpoints
│   ├── core/                # Core functionality
│   ├── models/              # Pydantic models
│   └── services/            # External integrations
├── main.py                  # FastAPI application
├── requirements.txt         # Python dependencies
└── README.md
```

### Adding New Features

1. **Models**: Add Pydantic models in `app/models/`
2. **Routes**: Create API endpoints in `app/api/routes/`
3. **Services**: Add external integrations in `app/services/`
4. **Core**: Add business logic in `app/core/`

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

## Entity Recognition Example

The system automatically identifies and tracks entities:

```python
# When you add content like:
"Met with Clare Johnson from Acme Corp about the Q4 project. 
She's based in San Francisco and handles their marketing initiatives."

# The system extracts:
# - Person: Clare Johnson
# - Organization: Acme Corp  
# - Location: San Francisco
# - Project: Q4 project

# Later, searching for "Clare" returns all related information
```

## Smart Memory Features

- **Automatic Relationship Building**: Links related entities and topics
- **Context Preservation**: Maintains conversation and document context
- **Smart Categorization**: Automatically organizes information by relevance
- **Temporal Tracking**: Tracks when and how information changes over time

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For support, please open an issue on GitHub or contact [your-email].

---

**Built with ❤️ for productivity and AI-powered personal organization**
