# J.A.R.V.I.S. — Advanced AI Desktop Assistant

An Iron Man-inspired desktop assistant featuring transparent glassmorphism UI layouts, real-time diagnostic telemetry, voice control, automated scheduled agents, OCR screen vision, directory observers, and persistent SQLite cognitive memory.

---

## 🚀 Key Features

*   **Multimodal Interaction**: Wake-word activation ("Jarvis"), continuous speech-to-text listening, interactive live wave visualizers, and text-to-speech synthesis (supporting neural Edge-TTS, local pyttsx3, or OpenAI Voice API).
*   **Central Control Cockpit**: A premium glassmorphism HUD featuring real-time CPU, RAM, Disk, Temperature, and GPU telemetry, active process monitoring, directory watchers, clipboard logs, and memory database explorer.
*   **Command Palette**: Press `Ctrl + K` inside the Electron window to summon the systems palette to run search queries and execute scripts.
*   **Background Automations**: Full SQLite-backed task scheduling (interval/cron engines) for auto-running shell commands and scanning folders to sort newly created files by category extension.
*   **Intelligent Agent Matrix**: Modular plugin architecture (e.g. weather tracking, Google/local calendar scheduler, GitHub repositories explorer) with gated approvals requiring explicit permission before executing administrative, deletion, or terminal commands.
*   **Dual UI/CLI Prompt**: Converse either through the glowing holographic Electron desktop app or input directives straight into the backend API server terminal.

---

## 🛠️ Technology Stack

*   **Backend Core**: Python 3.10+, FastAPI (Asynchronous API & WebSockets), SQLite (SQLAlchemy & aiosqlite).
*   **LLM Providers**: Switchable Google Gemini API, OpenAI GPT, or Ollama (local models).
*   **Automation Engines**: APScheduler (schedules), Watchdog (folders monitor).
*   **System Diagnostics**: psutil, nvidia-smi.
*   **Speech & Control**: SpeechRecognition, edge-tts, pyttsx3, PyAutoGUI, pytesseract OCR.
*   **Frontend UI**: Electron, React, TailwindCSS, Framer Motion, Lucide icons.

---

## 📂 Project Structure

```text
jarvis/
├── ai/                # LLM Managers (Gemini/OpenAI/Ollama)
├── api/               # API Routes & WebSockets
├── automation/        # APScheduler Task & Folder Watchers
├── config/            # Settings Config Mapping
├── core/              # Orchestrator & Tool Registry
├── database/          # SQLite Models & Engine Context
├── memory/            # Long-term Key-Value Facts
├── plugins/           # Calendar, GitHub, and Weather modules
├── speech/            # Wake Word, STT, and TTS engines
├── tests/             # Backend Pytest coverage
├── tools/             # PyAutoGUI controls, OCR, & Brightness
├── ui/                # React (Vite) + Electron client
└── start-all.bat      # Systems launcher script
```

---

## ⚙️ Installation & Setup

### Prerequisites

1.  **Python 3.10+**: Ensure Python is added to your Windows Environment `PATH`.
2.  **Node.js & npm**: Required to build and launch the Electron frontend.
3.  **Tesseract OCR** (Optional but recommended for screen OCR tools):
    *   Download and install the Windows installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
    *   By default, J.A.R.V.I.S. looks for it at `C:\Program Files\Tesseract-OCR\tesseract.exe`.

### 1. Backend Setup

Initialize a Python virtual environment and install package dependencies:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the root workspace folder to define your API keys:
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
GITHUB_TOKEN=your-github-token-for-plugin
```

### 2. Frontend Setup

Install Node dependencies:
```powershell
cd ui
npm install
cd ..
```

---

## 🚦 Quick Start

To launch J.A.R.V.I.S. in single-click launch mode, run the startup script:
```powershell
.\start-all.bat
```
This automatically starts:
1.  **FastAPI Server (`localhost:8000`)** which loads the database, registers the scheduler tasks, starts the folder observers, and spawns the background wake-word listener thread.
2.  **Vite + Electron App Window** with transparent glass backdrop frames and live wave meters.

---

## ⌨️ Operating Modes

### 1. Desktop GUI Cockpit
*   **Hologram Center**: Click the central glowing blue microphone button to speak or interrupt speech.
*   **HUD Tabs Sidebar**: View system analytics, kill high-memory processes, manage scheduled tasks, add key-value facts to memory, read active clipboard clips, or view live screenshot/webcam feeds.
*   **Command Dialogue**: Press `Ctrl + K` to open the palette and type search keywords.

### 2. Interactive Terminal Console CLI
You can type commands directly into the backend API server console window when running!
```text
============================================================
  J.A.R.V.I.S. INTERACTIVE CONSOLE ONLINE
  Type your commands/queries directly into the console, Sir.
============================================================

Sir > Search files for report.pdf
Sir > Remember my favorite project name is IronMan
```

---

## 🔒 Security Directives
J.A.R.V.I.S. is built with an active authorization gate. Dangerous tools (such as file deletes, folder organizing, or terminal executions) will pause speech queues and pop up a **Security directive modal card** on the Electron screen. The action is held inside an async future waiting for the user to select `Authorize Access` before continuing.
