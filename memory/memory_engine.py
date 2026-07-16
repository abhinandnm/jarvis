"""
Memory Engine — Manages JARVIS long-term memory stored in SQLite.
Supports saving facts, querying relevant memories, listing, and deleting.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.future import select
from database.database import AsyncSessionLocal
from database.models import MemoryEntry

logger = logging.getLogger("jarvis.memory.engine")


class MemoryEngine:
    """Persistent memory system for JARVIS."""

    async def save_memory_fact(self, key: str, value: str, category: str = "general") -> str:
        """
        Saves or updates a fact in the long-term memory database.

        Args:
            key: Unique identifier for the fact (e.g. 'user_birthday').
            value: The fact value (e.g. 'October 12').
            category: Fact category for organization and retrieval.

        Returns:
            str: Confirmation message.
        """
        clean_key = key.lower().strip().replace(" ", "_")
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(MemoryEntry).filter(MemoryEntry.key == clean_key)
                )
                entry = result.scalar_one_or_none()

                if entry:
                    logger.info(f"Updating memory: {clean_key} → '{value}'")
                    entry.value = value
                    entry.category = category
                else:
                    logger.info(f"Saving new memory: {clean_key} → '{value}'")
                    entry = MemoryEntry(key=clean_key, value=value, category=category)
                    session.add(entry)

                await session.commit()
                return f"Memory committed: '{clean_key}' = '{value}'."
            except Exception as e:
                logger.error(f"Failed to write memory: {e}")
                await session.rollback()
                return f"Failed to store memory: {str(e)}"

    async def get_relevant_memories(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Retrieves memory facts relevant to keywords in the user's prompt.

        Args:
            prompt: The user's input text to extract keywords from.

        Returns:
            List of matching memory fact dictionaries.
        """
        words = re.findall(r'\b\w{3,12}\b', prompt.lower())
        if not words:
            return []

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(select(MemoryEntry))
                all_entries = result.scalars().all()

                relevant = []
                for entry in all_entries:
                    key_words = entry.key.split("_")
                    cat_words = entry.category.split("_")

                    if any(w in key_words or w in cat_words or w in entry.value.lower() for w in words):
                        relevant.append({
                            "key": entry.key,
                            "value": entry.value,
                            "category": entry.category
                        })
                return relevant
            except Exception as e:
                logger.error(f"Failed to query memory: {e}")
                return []

    async def get_all_memories(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns all stored memory facts, optionally filtered by category.

        Args:
            category: Optional category filter string.

        Returns:
            List of memory fact dictionaries.
        """
        async with AsyncSessionLocal() as session:
            try:
                query = select(MemoryEntry).order_by(MemoryEntry.updated_at.desc())
                if category:
                    query = query.filter(MemoryEntry.category == category)
                result = await session.execute(query)
                entries = result.scalars().all()
                return [
                    {
                        "id": entry.id,
                        "key": entry.key,
                        "value": entry.value,
                        "category": entry.category,
                        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None
                    }
                    for entry in entries
                ]
            except Exception as e:
                logger.error(f"Failed to retrieve all memories: {e}")
                return []

    async def delete_memory(self, key: str) -> str:
        """
        Deletes a memory fact by key.

        Args:
            key: The fact key to delete.

        Returns:
            str: Confirmation or error message.
        """
        clean_key = key.lower().strip().replace(" ", "_")
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(MemoryEntry).filter(MemoryEntry.key == clean_key)
                )
                entry = result.scalar_one_or_none()
                if not entry:
                    return f"No memory found with key: '{clean_key}'"
                await session.delete(entry)
                await session.commit()
                return f"Memory '{clean_key}' deleted successfully."
            except Exception as e:
                logger.error(f"Failed to delete memory: {e}")
                await session.rollback()
                return f"Failed to delete memory: {str(e)}"

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Returns memory statistics for the UI dashboard."""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(select(MemoryEntry))
                entries = result.scalars().all()
                categories = {}
                for e in entries:
                    categories[e.category] = categories.get(e.category, 0) + 1
                return {
                    "total": len(entries),
                    "by_category": categories
                }
            except Exception as e:
                logger.error(f"Failed to get memory stats: {e}")
                return {"total": 0, "by_category": {}}


memory_engine = MemoryEngine()
