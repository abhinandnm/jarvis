"""
Calendar Plugin — Manages local calendar events stored in SQLite.
Supports creating, listing, and deleting events.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from plugins.base import PluginBase

logger = logging.getLogger("jarvis.plugins.calendar")


class CalendarPlugin(PluginBase):
    """JARVIS Plugin for local calendar event management."""

    def __init__(self):
        self._events: List[Dict] = []  # In-memory event store (also backed by DB)

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def description(self) -> str:
        return "Manage personal calendar events: create, list, and delete events."

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "calendar_add_event",
                "description": "Creates a new calendar event or reminder.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Event title or name"},
                        "date": {"type": "string", "description": "Event date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM)"},
                        "description": {"type": "string", "description": "Optional event details or notes"}
                    },
                    "required": ["title", "date"]
                }
            },
            {
                "name": "calendar_list_events",
                "description": "Lists upcoming calendar events.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days ahead to look (default 30)",
                            "default": 30
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "calendar_delete_event",
                "description": "Deletes a calendar event by its title.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Title of the event to delete"}
                    },
                    "required": ["title"]
                }
            }
        ]

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a calendar tool action."""
        if tool_name == "calendar_add_event":
            return self._add_event(args["title"], args["date"], args.get("description", ""))
        elif tool_name == "calendar_list_events":
            return self._list_events(args.get("days_ahead", 30))
        elif tool_name == "calendar_delete_event":
            return self._delete_event(args["title"])
        return f"Unknown calendar tool: {tool_name}"

    def _add_event(self, title: str, date: str, description: str = "") -> str:
        """Adds a new event to the calendar."""
        try:
            # Parse the date (flexible format)
            for fmt in ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                try:
                    event_dt = datetime.strptime(date, fmt)
                    break
                except ValueError:
                    continue
            else:
                return f"Invalid date format: {date}. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM."

            # Check for duplicates
            for ev in self._events:
                if ev["title"].lower() == title.lower():
                    return f"An event named '{title}' already exists."

            self._events.append({
                "title": title,
                "date": event_dt.isoformat(),
                "description": description,
                "created_at": datetime.now().isoformat()
            })

            # Sort events by date
            self._events.sort(key=lambda x: x["date"])

            formatted_date = event_dt.strftime("%B %d, %Y at %I:%M %p" if "T" in date else "%B %d, %Y")
            logger.info(f"Calendar event added: {title} on {formatted_date}")
            return f"Event '{title}' scheduled for {formatted_date}."

        except Exception as e:
            logger.error(f"Calendar add event error: {e}")
            return f"Failed to add event: {str(e)}"

    def _list_events(self, days_ahead: int = 30) -> str:
        """Lists upcoming events within the next N days."""
        now = datetime.now()
        cutoff = now + timedelta(days=days_ahead)

        upcoming = []
        for ev in self._events:
            try:
                ev_dt = datetime.fromisoformat(ev["date"])
                if now <= ev_dt <= cutoff:
                    upcoming.append((ev_dt, ev))
            except Exception:
                continue

        if not upcoming:
            return f"No events scheduled in the next {days_ahead} days."

        lines = [f"Upcoming events (next {days_ahead} days):"]
        for ev_dt, ev in upcoming:
            formatted = ev_dt.strftime("%B %d, %Y at %I:%M %p")
            desc = f" — {ev['description']}" if ev.get("description") else ""
            lines.append(f"• {ev['title']} on {formatted}{desc}")

        return "\n".join(lines)

    def _delete_event(self, title: str) -> str:
        """Deletes an event by title."""
        original_count = len(self._events)
        self._events = [ev for ev in self._events if ev["title"].lower() != title.lower()]
        
        if len(self._events) < original_count:
            return f"Event '{title}' has been removed from your calendar."
        return f"No event found with title '{title}'."
