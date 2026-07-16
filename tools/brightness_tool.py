"""
Brightness Control Tool — Adjusts screen brightness on Windows.
Uses PowerShell WMI commands since Windows doesn't expose brightness
via standard Python libraries on all hardware.
Falls back gracefully on unsupported hardware.
"""

import logging
import subprocess
import platform

logger = logging.getLogger("jarvis.tools.brightness")


class BrightnessTool:
    """Controls display brightness on Windows systems."""

    def set_brightness(self, level: int) -> str:
        """
        Sets the screen brightness to the specified level.

        Args:
            level: Brightness percentage (0-100).

        Returns:
            str: Status message.
        """
        level = max(0, min(100, int(level)))

        if platform.system() != "Windows":
            return "Brightness control is only supported on Windows."

        try:
            # Primary method: WMI via PowerShell (works on most laptops)
            ps_cmd = (
                f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                f".WmiSetBrightness(1,{level})"
            )
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"Brightness set to {level}%.")
                return f"Display brightness set to {level}%."
            else:
                # Fallback: Try screen-brightness-control package
                return self._set_brightness_sbc(level)

        except subprocess.TimeoutExpired:
            return "Brightness adjustment timed out."
        except Exception as e:
            logger.error(f"Brightness set error: {e}")
            return self._set_brightness_sbc(level)

    def _set_brightness_sbc(self, level: int) -> str:
        """Fallback brightness control using screen-brightness-control package."""
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(level)
            return f"Display brightness set to {level}% via screen control."
        except ImportError:
            return (
                "Brightness control requires 'screen-brightness-control' package. "
                "Run: pip install screen-brightness-control"
            )
        except Exception as e:
            return f"Could not adjust brightness: {str(e)}. Your hardware may not support software brightness control."

    def get_brightness(self) -> str:
        """
        Retrieves the current screen brightness.

        Returns:
            str: Current brightness percentage or error message.
        """
        try:
            ps_cmd = (
                "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
            )
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                level = result.stdout.strip()
                return f"Current display brightness: {level}%."
            return "Could not retrieve current brightness level."
        except Exception as e:
            logger.error(f"Get brightness error: {e}")
            return f"Error reading brightness: {str(e)}"


brightness_tool = BrightnessTool()
