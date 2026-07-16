import os
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger("jarvis.tools.os_control")

# Try importing pycaw for Windows volume control
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False

class OSController:
    def __init__(self):
        pass

    def open_application(self, app_name: str) -> str:
        """Opens common system applications or executes file/folder launches."""
        app_name_lower = app_name.lower().strip()
        
        # Standard mappings for common Windows apps
        common_apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "taskmgr": "taskmgr.exe",
            "chrome": "chrome.exe",
            "browser": "explorer.exe http://www.google.com"
        }
        
        try:
            if app_name_lower in common_apps:
                exec_name = common_apps[app_name_lower]
                subprocess.Popen(exec_name, shell=True)
                return f"Successfully opened {app_name}."
            
            # Fallback: attempt to run it directly as a start command or registry search
            logger.info(f"App name '{app_name}' not in standard map. Attempting os.startfile or start command.")
            # Verify if it's a valid path
            if os.path.exists(app_name):
                os.startfile(app_name)
                return f"Opened file/folder at path: {app_name}."
                
            # Run start command
            subprocess.Popen(f"start {app_name}", shell=True)
            return f"Requested Windows launch for: '{app_name}'."
            
        except Exception as e:
            logger.error(f"Error opening application {app_name}: {e}")
            return f"Failed to open {app_name}. Error details: {str(e)}"

    def close_application(self, process_name: str) -> str:
        """Kills processes on Windows using taskkill."""
        # Ensure process extension is present
        if not process_name.endswith(".exe") and not process_name.lower() in ["notepad", "calc", "chrome", "explorer"]:
            proc_exec = f"{process_name}.exe"
        else:
            proc_exec = process_name
            
        if not proc_exec.endswith(".exe"):
            proc_exec += ".exe"
            
        logger.info(f"Attempting to terminate process: {proc_exec}")
        try:
            # Run taskkill
            cmd = f"taskkill /F /IM {proc_exec}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"Process {proc_exec} terminated successfully."
            else:
                return f"Could not find or terminate {proc_exec}. (Output: {result.stderr.strip()})"
        except Exception as e:
            logger.error(f"Failed to close process {process_name}: {e}")
            return f"Error occurred while closing {process_name}: {str(e)}"

    def set_system_volume(self, level: int) -> str:
        """Sets main audio volume. Value between 0 and 100."""
        # Constrain level
        level = max(0, min(100, level))
        
        if PYCAW_AVAILABLE:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                
                # Volume expects scalar between 0.0 and 1.0 (or dB values)
                scalar = level / 100.0
                volume.SetMasterVolumeLevelScalar(scalar, None)
                return f"System volume set to {level}%."
            except Exception as e:
                logger.error(f"Pycaw volume error: {e}")
                # Fallback to pyautogui simulation if pycaw fails
                return self._volume_pyautogui_fallback(level)
        else:
            return self._volume_pyautogui_fallback(level)

    def _volume_pyautogui_fallback(self, level: int) -> str:
        """Alternative: pyautogui sound keystrokes simulation."""
        try:
            import pyautogui
            # PyAutoGUI doesn't have an absolute volume setter, but we can send volume-down multiple times, then volume-up
            # Send 50 volume down strokes to mute/zero-out, then volume up to level (each volume up key press is typically 2%)
            for _ in range(50):
                pyautogui.press("volumedown")
            for _ in range(int(level / 2)):
                pyautogui.press("volumeup")
            return f"Simulated volume adjustment set to approximately {level}%."
        except Exception as e:
            logger.error(f"Pyautogui volume fallback failed: {e}")
            return "Volume adjustment is currently unavailable on this platform."

    def execute_terminal_command(self, command: str) -> str:
        """Executes administrative or shell commands safely."""
        logger.info(f"Executing shell command: '{command}'")
        try:
            # Execute command with a timeout of 10 seconds to prevent hanging
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10.0)
            output = result.stdout
            err = result.stderr
            
            resp = ""
            if output:
                resp += f"Output:\n{output.strip()}\n"
            if err:
                resp += f"Errors:\n{err.strip()}\n"
            if not resp:
                resp = "Command executed with no output returned."
            return resp
        except subprocess.TimeoutExpired:
            return "Command execution timed out (maximum limit of 10s exceeded)."
        except Exception as e:
            logger.error(f"Shell command error: {e}")
            return f"Failed to execute command: {str(e)}"

os_controller = OSController()
