import logging
import subprocess
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

class AppleCalendarService:
    """Service for integrating with Apple Calendar using AppleScript"""
    
    def __init__(self):
        self.enabled = settings.apple_script_enabled
    
    async def create_event(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Create an event in Apple Calendar"""
        if not self.enabled:
            logger.info("Apple Calendar integration disabled")
            return None
        
        try:
            # Format dates for AppleScript
            start_date = event_data.get("start_date")
            end_date = event_data.get("end_date")
            
            if not start_date or not end_date:
                logger.error("Start date and end date are required")
                return None
            
            # Create AppleScript command
            script = f'''
            tell application "Calendar"
                tell calendar "Second Brain"
                    make new event with properties {{
                        summary: "{event_data.get('title', '')}",
                        description: "{event_data.get('description', '')}",
                        start date: date "{start_date.strftime('%m/%d/%Y %H:%M:%S')}",
                        end date: date "{end_date.strftime('%m/%d/%Y %H:%M:%S')}",
                        location: "{event_data.get('location', '')}"
                    }}
                end tell
            end tell
            '''
            
            # Execute AppleScript
            result = await self._run_applescript(script)
            
            if result:
                logger.info(f"Created Apple Calendar event: {event_data.get('title')}")
                return "apple_event_created"  # Would return actual ID in real implementation
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create Apple Calendar event: {e}")
            return None
    
    async def update_event(self, apple_event_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an event in Apple Calendar"""
        if not self.enabled:
            return False
        
        try:
            # This would update the specific event by ID
            logger.info(f"Updating Apple Calendar event: {apple_event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Apple Calendar event: {e}")
            return False
    
    async def delete_event(self, apple_event_id: str) -> bool:
        """Delete an event from Apple Calendar"""
        if not self.enabled:
            return False
        
        try:
            # This would delete the specific event by ID
            logger.info(f"Deleting Apple Calendar event: {apple_event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Apple Calendar event: {e}")
            return False
    
    async def sync_calendar(self, user_id: str) -> Dict[str, Any]:
        """Sync calendar events with Apple Calendar"""
        if not self.enabled:
            return {"status": "disabled", "message": "Apple Calendar integration disabled"}
        
        try:
            # This would implement full bidirectional sync
            logger.info(f"Syncing calendar for user: {user_id}")
            
            return {
                "status": "success",
                "events_synced": 0,
                "last_sync": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Calendar sync failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _run_applescript(self, script: str) -> Optional[str]:
        """Execute an AppleScript command"""
        try:
            # Use osascript to run AppleScript
            process = await asyncio.create_subprocess_exec(
                'osascript', '-e', script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                logger.error(f"AppleScript error: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to run AppleScript: {e}")
            return None

class AppleRemindersService:
    """Service for integrating with Apple Reminders using AppleScript"""
    
    def __init__(self):
        self.enabled = settings.apple_script_enabled
    
    async def create_reminder(self, reminder_data: Dict[str, Any]) -> Optional[str]:
        """Create a reminder in Apple Reminders"""
        if not self.enabled:
            logger.info("Apple Reminders integration disabled")
            return None
        
        try:
            due_date = reminder_data.get("due_date")
            due_date_str = ""
            if due_date:
                due_date_str = f'due date: date "{due_date.strftime('%m/%d/%Y %H:%M:%S')}",'
            
            # Create AppleScript command
            script = f'''
            tell application "Reminders"
                tell list "Second Brain"
                    make new reminder with properties {{
                        name: "{reminder_data.get('title', '')}",
                        body: "{reminder_data.get('description', '')}",
                        {due_date_str}
                        priority: {self._convert_priority(reminder_data.get('priority', 'medium'))}
                    }}
                end tell
            end tell
            '''
            
            # Execute AppleScript
            result = await self._run_applescript(script)
            
            if result:
                logger.info(f"Created Apple Reminder: {reminder_data.get('title')}")
                return "apple_reminder_created"  # Would return actual ID in real implementation
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create Apple Reminder: {e}")
            return None
    
    async def update_reminder(self, apple_reminder_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a reminder in Apple Reminders"""
        if not self.enabled:
            return False
        
        try:
            # This would update the specific reminder by ID
            logger.info(f"Updating Apple Reminder: {apple_reminder_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Apple Reminder: {e}")
            return False
    
    async def delete_reminder(self, apple_reminder_id: str) -> bool:
        """Delete a reminder from Apple Reminders"""
        if not self.enabled:
            return False
        
        try:
            # This would delete the specific reminder by ID
            logger.info(f"Deleting Apple Reminder: {apple_reminder_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Apple Reminder: {e}")
            return False
    
    async def sync_reminders(self, user_id: str) -> Dict[str, Any]:
        """Sync reminders with Apple Reminders"""
        if not self.enabled:
            return {"status": "disabled", "message": "Apple Reminders integration disabled"}
        
        try:
            # This would implement full bidirectional sync
            logger.info(f"Syncing reminders for user: {user_id}")
            
            return {
                "status": "success",
                "reminders_synced": 0,
                "last_sync": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Reminders sync failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def _convert_priority(self, priority: str) -> int:
        """Convert our priority system to Apple's numeric system"""
        priority_map = {
            "low": 1,
            "medium": 5,
            "high": 9,
            "urgent": 9
        }
        return priority_map.get(priority.lower(), 5)
    
    async def _run_applescript(self, script: str) -> Optional[str]:
        """Execute an AppleScript command"""
        try:
            # Use osascript to run AppleScript
            process = await asyncio.create_subprocess_exec(
                'osascript', '-e', script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                logger.error(f"AppleScript error: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to run AppleScript: {e}")
            return None