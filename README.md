# CognitBotz Voice AI Consultant

A complete, production-grade conversational Voice AI Consultant application designed for local speech processing, context-grounded retrieval-augmented generation (RAG), and natural Indian female voice synthesis.

## 🚀 Recent Architecture Upgrades

The system has been completely modernized, migrating from a monolithic Streamlit application to a decoupled, high-performance web architecture:

- **Frontend**: Next.js (React) application featuring a beautiful, dynamic glassmorphic UI, real-time voice recording, and dedicated text/voice input modes.
- **Backend**: FastAPI providing robust REST endpoints, full CORS support, and asynchronous request handling.
- **Unified Startup**: A PowerShell script (`start.ps1`) to spin up both the Next.js dev server and the Python FastAPI backend simultaneously.

---

## 🧠 Architecture Overview

Aria, the Voice AI Consultant, processes queries through a modular, low-latency pipeline:

1. **Audio Input**: Real-time browser audio recording natively converted to speech-to-text.
2. **Audio Processing**: Transcription via Faster Whisper (`small.en`).
3. **Knowledge Retrieval**: Query embedding (BGE Small v1.5) and search against a local vector database (FAISS) containing chunked company facts.
4. **LLM Orchestration**: Groq API (Llama 3 / DeepSeek R1 fallback) with sliding window memory and RAG context grounding.
5. **Voice Synthesis**: Response text normalisation and neural speech synthesis (Piper TTS) using a local ONNX model.
6. **Interface**: Responsive Next.js layout displaying live status, chat bubbles, source citations, and latency metrics per pipeline stage.

---

## 📁 Project Structure

```text
CognitBotz-voice-agent/
│
├── knowledge_base_master.md    # Source document containing organization facts
├── README.md                   # Setup and usage guide
├── start.ps1                   # Unified startup script for both frontend and backend
│
├── frontend/                   # Next.js React Application
│   ├── src/
│   │   ├── app/                # Next.js App Router (page.tsx, globals.css)
│   │   ├── components/         # React UI Components (InputArea, ChatInterface, etc.)
│   │   └── store/              # Zustand global state (conversationStore.ts)
│   ├── tailwind.config.ts      # Tailwind CSS styling configuration
│   └── package.json            # Node.js dependencies
│
└── voice_agent/                # Core Python Backend
    ├── api/                    # FastAPI server (server.py)
    ├── run_ingestion.py        # Offline FAISS index ingestion script
    ├── .env                    # Application configuration variables
    ├── requirements.txt        # Python dependency manifest
    │
    ├── config/                 # Application configuration & prompts
    ├── utils/                  # Logging, performance metrics, & validation
    ├── audio/                  # STT (Faster Whisper) & TTS (Piper)
    ├── rag/                    # Retrieval-Augmented Generation (FAISS)
    ├── llm/                    # Groq API client & response assembly
    ├── memory/                 # HistoryManager and sliding-window context
    └── backend/                # Pipeline orchestrator
```

---

## 🛠️ Installation & Setup

### 1. Prerequisites
- **Python**: Recommended version `3.10.x` or `3.11.x`.
- **Node.js**: Recommended version `18.x` or higher (for the frontend).
- **Visual C++ Build Tools (Windows)**: Required for compiling native Python dependencies.

### 2. Set Up Python Backend
Create and activate a python virtual environment, then install dependencies:
```powershell
# Create environment
python -m venv venv_py311

# Activate on Windows (PowerShell)
.\venv_py311\Scripts\Activate.ps1

# Install requirements
pip install -r voice_agent/requirements.txt
```

### 3. Set Up Node Frontend
Install the React application dependencies:
```powershell
cd frontend
npm install
cd ..
```

### 4. Configure Environment Variables
Open the `voice_agent/.env` file and add your **Groq API Key**:
```env
GROQ_API_KEY=gsk_your_actual_key_here
```
*(You can also adjust parameters such as model choices and memory window sizes here).*

Make sure the frontend is configured to talk to the backend. Create or edit `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🚀 Running the Application

### Step 1: Run Document Ingestion (RAG Indexing)
Before launching the interface, compile the vector search database from `knowledge_base_master.md`:
```powershell
# Ensure your virtual environment is active
python voice_agent/run_ingestion.py
```

### Step 2: Offline TTS Voice (one-time download)
The assistant uses **MMS VITS** (`onecxi/mms-english-female-indic`) — English speech with an **Indian female** speaker. Fully offline after the first run (model caches to `~/.cache/huggingface`).

```powershell
pip install piper-tts onnxruntime
# First API start downloads the MMS model automatically (~80 MB)
```

Optional Piper fallback (Indian English accent, faster CPU):

```env
TTS_ENGINE=piper
TTS_MODEL_PATH=voice_agent/assets/voices/en_IN-spicor-medium.onnx
```

Default `.env`:

```env
TTS_ENGINE=mms
TTS_MMS_MODEL_ID=onecxi/mms-english-female-indic
```

### Step 3: Start Services
Use the provided PowerShell script to launch both the FastAPI backend and the Next.js frontend simultaneously:
```powershell
.\start.ps1
```
- The **FastAPI Backend** will run on `http://localhost:8000` (check `backend.log` and `backend-error.log` for output).
- The **Next.js Frontend** will run on `http://localhost:3000` and automatically open in your default browser.
- Press `Ctrl+C` in the terminal to gracefully shut down both services.

---

## 🧪 Testing

A test suite is located in the `voice_agent/tests/` directory to validate RAG, Speech-to-Text, and Text-to-Speech logic.

To run the Python backend tests:
```bash
pytest voice_agent/tests/
```
