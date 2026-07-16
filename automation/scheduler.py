import asyncio
import datetime
import logging
from typing import Dict, Any, Callable, List

logger = logging.getLogger("jarvis.automation.scheduler")

class ScheduledTask:
    def __init__(self, name: str, interval_seconds: int, callback: Callable[[], Any]):
        self.name = name
        self.interval_seconds = interval_seconds
        self.callback = callback
        self.last_run = datetime.datetime.min
        self.is_running = False

    def is_due(self) -> bool:
        """Determines if the task is due for execution."""
        elapsed = (datetime.datetime.now() - self.last_run).total_seconds()
        return elapsed >= self.interval_seconds

class AutomationScheduler:
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.is_active = False
        self._loop_task = None

    def register_task(self, name: str, interval_seconds: int, callback: Callable[[], Any]):
        """Registers a recurring task."""
        self.tasks[name] = ScheduledTask(name, interval_seconds, callback)
        logger.info(f"Registered scheduled task '{name}' with interval of {interval_seconds} seconds.")

    def unregister_task(self, name: str):
        """Removes a task from schedule."""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Unregistered scheduled task '{name}'.")

    def start(self):
        """Starts the schedule executor loop."""
        if self.is_active:
            return
        self.is_active = True
        self._loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Automation scheduler loop started.")

    def stop(self):
        """Stops the scheduler loop."""
        self.is_active = False
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None
        logger.info("Automation scheduler loop stopped.")

    async def _scheduler_loop(self):
        """Core loop executing due tasks."""
        try:
            while self.is_active:
                # Check task list every 2 seconds
                await asyncio.sleep(2.0)
                
                for task in list(self.tasks.values()):
                    if task.is_due() and not task.is_running:
                        task.is_running = True
                        logger.info(f"Triggering scheduled task: {task.name}")
                        try:
                            # Execute task callback
                            if asyncio.iscoroutinefunction(task.callback):
                                await task.callback()
                            else:
                                await asyncio.to_thread(task.callback)
                        except Exception as e:
                            logger.error(f"Error executing scheduled task '{task.name}': {e}")
                        finally:
                            task.last_run = datetime.datetime.now()
                            task.is_running = False
                            
        except asyncio.CancelledError:
            pass  # Task cancelled

automation_scheduler = AutomationScheduler()
