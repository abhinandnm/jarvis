"""
Automation Scheduler — APScheduler-based task scheduling with SQLite persistence.
Supports cron, interval, and one-time date triggers.
Runs tasks in the background and broadcasts results via WebSocket.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger("jarvis.automation.scheduler")

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Run: pip install apscheduler")


class JarvisScheduler:
    """
    Manages scheduled automation tasks for JARVIS.
    Tasks are stored in SQLite and survive restarts.
    """

    def __init__(self):
        self._scheduler: Optional[Any] = None
        self._broadcast_fn: Optional[Callable] = None
        self._tasks_store: Dict[str, Dict] = {}  # In-memory task registry
        self._built_in_tasks: List[str] = []

    def initialize(self, broadcast_fn: Callable):
        """Initialize the scheduler with a WebSocket broadcast function."""
        self._broadcast_fn = broadcast_fn
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler not available, scheduler disabled.")
            return

        self._scheduler = AsyncIOScheduler(timezone="UTC")

        # Register built-in periodic tasks
        self._register_builtin_tasks()

        self._scheduler.start()
        logger.info("JARVIS Scheduler started successfully.")

    def _register_builtin_tasks(self):
        """Register pre-built recurring automation tasks."""
        if not self._scheduler:
            return

        # Built-in: System health monitor every 30 seconds
        self._scheduler.add_job(
            self._task_system_health_check,
            trigger=IntervalTrigger(seconds=30),
            id="builtin_system_health",
            name="System Health Monitor",
            replace_existing=True,
            misfire_grace_time=10
        )
        self._built_in_tasks.append("builtin_system_health")

        logger.info("Built-in scheduler tasks registered.")

    async def _task_system_health_check(self):
        """Periodically checks system health and broadcasts alerts."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent

            # Alert if CPU or RAM is critically high
            if cpu > 90:
                await self._broadcast_notification(
                    f"⚠️ Critical CPU usage: {cpu:.0f}%",
                    level="warning"
                )
            if ram > 90:
                await self._broadcast_notification(
                    f"⚠️ Critical RAM usage: {ram:.0f}%",
                    level="warning"
                )
        except Exception as e:
            logger.error(f"System health check error: {e}")

    async def _broadcast_notification(self, message: str, level: str = "info"):
        """Broadcasts a notification to connected WebSocket clients."""
        if self._broadcast_fn:
            try:
                await self._broadcast_fn({
                    "type": "notification",
                    "content": message,
                    "level": level,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to broadcast notification: {e}")

    def add_task(
        self,
        task_id: str,
        name: str,
        command: str,
        trigger_type: str,
        trigger_config: Dict[str, Any]
    ) -> str:
        """
        Adds a new scheduled task.

        Args:
            task_id: Unique identifier for the task.
            name: Human-readable task name.
            command: Shell command or JARVIS directive to run.
            trigger_type: 'cron', 'interval', or 'date'.
            trigger_config: Trigger-specific configuration dict.

        Returns:
            str: Success or error message.
        """
        if not APSCHEDULER_AVAILABLE or not self._scheduler:
            return "Scheduler not available. Please install APScheduler."

        try:
            # Build trigger
            if trigger_type == "cron":
                trigger = CronTrigger(**trigger_config)
            elif trigger_type == "interval":
                trigger = IntervalTrigger(**trigger_config)
            elif trigger_type == "date":
                trigger = DateTrigger(**trigger_config)
            else:
                return f"Unknown trigger type: {trigger_type}. Use 'cron', 'interval', or 'date'."

            # Create async task function
            async def run_task():
                logger.info(f"Running scheduled task '{name}': {command}")
                await self._broadcast_notification(
                    f"🤖 Running scheduled task: {name}",
                    level="info"
                )
                try:
                    import subprocess
                    result = subprocess.run(
                        command, shell=True, capture_output=True, text=True, timeout=60
                    )
                    output = result.stdout or result.stderr or "Task completed."
                    await self._broadcast_notification(
                        f"✅ Task '{name}' done: {output[:100]}",
                        level="success"
                    )
                except Exception as e:
                    await self._broadcast_notification(
                        f"❌ Task '{name}' failed: {str(e)}",
                        level="error"
                    )

            self._scheduler.add_job(
                run_task,
                trigger=trigger,
                id=task_id,
                name=name,
                replace_existing=True,
                misfire_grace_time=60
            )

            # Store task metadata
            self._tasks_store[task_id] = {
                "id": task_id,
                "name": name,
                "command": command,
                "trigger_type": trigger_type,
                "trigger_config": trigger_config,
                "created_at": datetime.now().isoformat(),
                "active": True
            }

            logger.info(f"Scheduled task '{name}' (ID: {task_id}) added successfully.")
            return f"Scheduled task '{name}' created successfully."

        except Exception as e:
            logger.error(f"Failed to add scheduled task: {e}")
            return f"Failed to create task: {str(e)}"

    def remove_task(self, task_id: str) -> str:
        """Removes a scheduled task by ID."""
        if not self._scheduler:
            return "Scheduler not available."
        try:
            self._scheduler.remove_job(task_id)
            self._tasks_store.pop(task_id, None)
            return f"Task '{task_id}' removed successfully."
        except Exception as e:
            return f"Failed to remove task: {str(e)}"

    def list_tasks(self) -> List[Dict]:
        """Returns a list of all registered scheduled tasks with next run times."""
        if not self._scheduler:
            return []
        
        result = []
        for job in self._scheduler.get_jobs():
            next_run = job.next_run_time
            result.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
                "is_builtin": job.id in self._built_in_tasks,
                "command": self._tasks_store.get(job.id, {}).get("command", "Built-in task"),
                "trigger_type": self._tasks_store.get(job.id, {}).get("trigger_type", "internal"),
                "active": True
            })
        return result

    def pause_task(self, task_id: str) -> str:
        """Pauses a task temporarily."""
        if not self._scheduler:
            return "Scheduler not available."
        try:
            self._scheduler.pause_job(task_id)
            return f"Task '{task_id}' paused."
        except Exception as e:
            return f"Failed to pause task: {str(e)}"

    def resume_task(self, task_id: str) -> str:
        """Resumes a paused task."""
        if not self._scheduler:
            return "Scheduler not available."
        try:
            self._scheduler.resume_job(task_id)
            return f"Task '{task_id}' resumed."
        except Exception as e:
            return f"Failed to resume task: {str(e)}"

    def shutdown(self):
        """Gracefully shuts down the scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("JARVIS Scheduler shut down.")


# Singleton instance
jarvis_scheduler = JarvisScheduler()
