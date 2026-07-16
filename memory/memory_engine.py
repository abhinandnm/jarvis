import logging
import re
from typing import List, Dict, Any
from sqlalchemy.future import select
from database.database import AsyncSessionLocal
from database.models import MemoryEntry

logger = logging.getLogger("jarvis.memory.engine")

class MemoryEngine:
    def __init__(self):
        pass

    async def save_memory_fact(self, key: str, value: str, category: str = "general") -> str:
        """Saves or updates a fact in the long-term memory database."""
        clean_key = key.lower().strip().replace(" ", "_")
        async with AsyncSessionLocal() as session:
            try:
                # Check if key already exists
                result = await session.execute(
                    select(MemoryEntry).filter(MemoryEntry.key == clean_key)
                )
                entry = result.scalar_one_or_none()
                
                if entry:
                    logger.info(f"Updating memory fact: {clean_key} -> '{value}'")
                    entry.value = value
                    entry.category = category
                else:
                    logger.info(f"Saving new memory fact: {clean_key} -> '{value}'")
                    entry = MemoryEntry(
                        key=clean_key,
                        value=value,
                        category=category
                    )
                    session.add(entry)
                
                await session.commit()
                return f"I have committed that to my memory matrix: '{clean_key}' is '{value}'."
            except Exception as e:
                logger.error(f"Failed to write memory: {e}")
                await session.rollback()
                return f"I failed to store that memory. Matrix error: {str(e)}"

    async def get_relevant_memories(self, prompt: str) -> List[Dict[str, Any]]:
        """Queries memories that are relevant to keywords in the user's prompt."""
        # Simple keyword extraction: strip punctuation and split words
        words = re.findall(r'\b\w{3,12}\b', prompt.lower())
        if not words:
            return []

        async with AsyncSessionLocal() as session:
            try:
                # Query all memory entries
                result = await session.execute(select(MemoryEntry))
                all_entries = result.scalars().all()
                
                relevant = []
                # Check for word overlaps or direct category matches
                for entry in all_entries:
                    key_words = entry.key.split("_")
                    category_words = entry.category.split("_")
                    
                    # If any keyword matches a word in the prompt, it's relevant
                    match = False
                    for w in words:
                        if w in key_words or w in category_words or w in entry.value.lower():
                            match = True
                            break
                            
                    if match:
                        relevant.append({
                            "key": entry.key,
                            "value": entry.value,
                            "category": entry.category
                        })
                return relevant
            except Exception as e:
                logger.error(f"Failed to query memory: {e}")
                return []

memory_engine = MemoryEngine()
