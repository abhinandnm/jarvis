import datetime
import json
from sqlalchemy import Column, String, Integer, DateTime, Text, Float, Boolean
from database.database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, default="default", index=True)
    role = Column(String)  # 'user', 'assistant', or 'tool'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    provider = Column(String, nullable=True)   # Also used for tool_call_id
    model = Column(String, nullable=True)      # Also used for tool name


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)
    category = Column(String, default="general")  # 'preference', 'project', 'app', 'website', 'task'
    confidence = Column(Float, default=1.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ScheduledTask(Base):
    """Persistent record of JARVIS automation tasks."""
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    command = Column(Text)                   # Shell command or JARVIS directive
    trigger_type = Column(String)            # 'cron', 'interval', 'date'
    trigger_config = Column(Text)            # JSON-encoded trigger parameters
    is_active = Column(Boolean, default=True)
    is_builtin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)


class Notification(Base):
    """History of JARVIS system notifications."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text)
    level = Column(String, default="info")    # 'info', 'warning', 'error', 'success'
    source = Column(String, nullable=True)   # e.g. 'scheduler', 'system', 'agent'
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ClipboardHistory(Base):
    """History of clipboard entries tracked by JARVIS."""
    __tablename__ = "clipboard_history"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    preview = Column(String)                  # Truncated preview
    content_type = Column(String, default="text")  # 'text', 'url', 'code', 'path'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

