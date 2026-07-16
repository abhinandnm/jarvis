import pytest
import asyncio
from sqlalchemy.future import select
from config.config import settings
from database.database import init_db, AsyncSessionLocal
from database.models import ChatHistory, MemoryEntry
from ai.llm import llm_manager

# Set up event loop for asyncio testing
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_database_initialization():
    """Verify that SQLite database initializes and creates tables."""
    # Force settings to use an in-memory testing database and recreate engine
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    
    import database.database
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    database.database.engine = create_async_engine(settings.DATABASE_URL, echo=False)
    database.database.AsyncSessionLocal = async_sessionmaker(
        bind=database.database.engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    global AsyncSessionLocal
    AsyncSessionLocal = database.database.AsyncSessionLocal
    
    # Initialize DB
    await init_db()
    
    # Assert database sessions can write and read
    async with AsyncSessionLocal() as session:
        # Create a test message
        test_msg = ChatHistory(
            session_id="test_session",
            role="user",
            content="Hello J.A.R.V.I.S.",
            provider="mock",
            model="mock-model"
        )
        session.add(test_msg)
        await session.commit()
        
        # Query it back
        result = await session.execute(
            select(ChatHistory).filter(ChatHistory.session_id == "test_session")
        )
        messages = result.scalars().all()
        
        assert len(messages) == 1
        assert messages[0].content == "Hello J.A.R.V.I.S."
        assert messages[0].role == "user"

@pytest.mark.asyncio
async def test_memory_creation():
    """Verify that memory entries can be created and queried."""
    async with AsyncSessionLocal() as session:
        # Insert a fact
        fact = MemoryEntry(
            key="user_real_name",
            value="Tony Stark",
            category="preference",
            confidence=0.99
        )
        session.add(fact)
        await session.commit()
        
        # Query back
        result = await session.execute(
            select(MemoryEntry).filter(MemoryEntry.key == "user_real_name")
        )
        entry = result.scalar_one_or_none()
        
        assert entry is not None
        assert entry.value == "Tony Stark"
        assert entry.confidence == 0.99

def test_settings_loaded():
    """Verify default configurations are set properly."""
    assert settings.API_HOST == "127.0.0.1"
    assert settings.API_PORT == 8000
    assert settings.WAKE_WORD == "jarvis"
