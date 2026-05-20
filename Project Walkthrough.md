# Project Walkthrough: CognitBotz Voice AI Consultant

## 1. Project Overview

This project is a full voice-enabled AI customer clarification agent for CognitBotz. The assistant is named Aria. It allows a user to ask questions by voice or text, sends the question through a backend intelligence pipeline, generates a grounded answer from the CognitBotz knowledge base, displays the answer as text, and also generates a spoken audio response.

The system is designed to feel like a natural customer-facing conversation instead of a simple FAQ bot. Aria can answer questions about the company, services, AI solutions, automation capabilities, industries served, technologies, products, case studies, contact details, and related business information. It also keeps session memory, so a user can ask questions like "what was my previous question?" and the assistant can answer correctly within the current session.

The project has two main experiences:

- A modern Next.js frontend for the main website-style chat interface.
- A Python FastAPI backend that handles speech recognition, retrieval, LLM response generation, text-to-speech, session memory, and API responses.

There is also an older Streamlit interface inside `voice_agent/frontend/`, but the modern frontend is the React/Next.js app in the root `frontend/` folder.

## 2. What Has Been Built

You have built a complete voice AI consultant application with the following capabilities:

- Voice input from the browser microphone.
- Text input for typed questions.
- Speech-to-text transcription using Faster Whisper.
- Retrieval-Augmented Generation using a CognitBotz knowledge base.
- FAISS vector search for finding relevant company information.
- Groq LLM integration for generating natural language answers.
- Text-to-speech voice synthesis using local Piper.
- Automatic playback of the generated answer audio.
- Manual replay controls for listening again.
- Session memory for follow-up questions and memory-based questions.
- Clean black-themed modern frontend UI.
- Source cards showing where information came from.
- Latency metrics showing pipeline timing.
- REST API endpoints for text chat, audio chat, history, and clearing history.
- Test coverage for memory, pipeline behavior, and text-to-speech.

In short, the application behaves like a customer clarification agent that can listen, understand, search company knowledge, answer naturally, speak the answer, and remember the current conversation.

## 3. High-Level Architecture

The project is split into two main folders:

```text
CognitBotz-voice-agent/
  frontend/        Modern Next.js frontend
  voice_agent/     Python backend, RAG, LLM, audio, memory, tests
```

The user interacts with the frontend. The frontend sends requests to the FastAPI backend. The backend performs the AI pipeline and returns text, audio, sources, and timing information.

High-level flow:

```text
User speaks or types
  -> Frontend captures input
  -> FastAPI receives request
  -> Speech-to-text if audio
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Zustand for client-side conversation state
- Axios for API calls
- Framer Motion for subtle message animation
```text
frontend/src/app/page.tsx
frontend/src/app/globals.css
frontend/src/components/Header.tsx
frontend/src/components/ChatInterface.tsx
frontend/src/components/ChatMessage.tsx
frontend/src/components/InputArea.tsx
frontend/src/components/AudioPlayer.tsx
frontend/src/components/SourceCards.tsx
frontend/src/components/LatencyBadge.tsx
frontend/src/store/conversationStore.ts
frontend/tailwind.config.ts
```

### Backend

The backend is built with:

- Python
- FastAPI
- Uvicorn
- Faster Whisper for speech-to-text
- Sentence Transformers for embeddings
- BAAI/bge-small-en-v1.5 as the embedding model
- FAISS for vector search
- Groq API for LLM responses
- Piper (local) for speech synthesis
- Pytest for tests

The backend lives in:

```text
voice_agent/
```

Important backend files:

```text
voice_agent/api/server.py
voice_agent/backend/orchestrator.py
voice_agent/audio/speech_to_text.py
voice_agent/audio/text_to_speech.py
voice_agent/rag/retrieval.py
voice_agent/rag/vector_store.py
voice_agent/rag/chunking.py
voice_agent/rag/embeddings.py
voice_agent/llm/groq_client.py
voice_agent/llm/response_generator.py
voice_agent/llm/prompt_builder.py
voice_agent/memory/conversation_memory.py
voice_agent/memory/history_manager.py
voice_agent/config/prompts.py
voice_agent/config/settings.py
voice_agent/utils/helpers.py
voice_agent/utils/performance.py
```

## 5. Knowledge Base and RAG

The assistant answers from a CognitBotz knowledge base. The main knowledge file is:

```text
voice_agent/data/knowledge_base_master.md
```

There is also a root-level source file:

```text
knowledge_base_master.md
```

The backend uses Retrieval-Augmented Generation, usually called RAG. This means the assistant does not simply answer from the LLM's general knowledge. Instead, the user question is used to search the company knowledge base, and the most relevant chunks are passed to the LLM as context.

The RAG flow works like this:

1. The knowledge base is split into smaller chunks.
2. Each chunk is converted into an embedding vector.
3. The vectors are stored in a local FAISS index.
4. When the user asks a question, the question is also converted into an embedding.
5. FAISS finds the most similar knowledge chunks.
6. Those chunks are passed into the LLM prompt.
7. The LLM answers using that retrieved context.

The FAISS index lives here:

```text
voice_agent/data/faiss_index/
```

The ingestion script is:

```text
voice_agent/run_ingestion.py
```

This script builds or refreshes the FAISS index from the knowledge base.

## 6. Backend API

The FastAPI server is defined in:

```text
voice_agent/api/server.py
```

It exposes the backend pipeline to the frontend.

Main endpoints:

```text
GET  /api/health
POST /api/chat/text
POST /api/chat/audio
GET  /api/history
POST /api/history/clear
```

### `/api/chat/text`

This endpoint receives a typed question.

Input example:

```json
{
  "text": "What services does CognitBotz offer?"
}
```

It returns:

- `success`
- `transcript`
- `response_text`
- `audio_bytes_b64`
- `audio_sample_rate`
- `source_cards`
- `latency`

The frontend uses `response_text` for the chat bubble and `audio_bytes_b64` for the audio player.

### `/api/chat/audio`

This endpoint receives a recorded audio file from the browser.

It performs the full voice pipeline:

```text
audio file -> transcription -> RAG -> LLM -> TTS -> response
```

It returns the same kind of response as text chat, but also includes the transcript detected from the user's voice.

### `/api/history`

This endpoint returns the current session's message history.

### `/api/history/clear`

This endpoint clears the conversation history and starts a fresh session.

## 7. Main Backend Pipeline

The central backend pipeline is controlled by:

```text
voice_agent/backend/orchestrator.py
```

The main class is:

```python
PipelineOrchestrator
```

It coordinates:

- Speech-to-text
- Knowledge retrieval
- LLM response generation
- Text-to-speech synthesis
- Latency measurement
- Final response packaging

There are two main entry points:

```python
process_audio(...)
process_text(...)
```

### Text Pipeline

When the user types a question:

1. The frontend calls `/api/chat/text`.
2. FastAPI calls `orchestrator.process_text(...)`.
3. The query is sent to the retriever.
4. The retriever returns relevant knowledge base chunks.
5. The response generator builds a prompt.
6. Groq generates a text response.
7. The response is normalized for speech.
8. Piper generates audio.
9. The backend returns text and base64 audio to the frontend.

### Voice Pipeline

When the user speaks:

1. The browser records microphone audio.
2. The frontend sends the audio blob to `/api/chat/audio`.
3. FastAPI reads the uploaded file.
4. The orchestrator calls Faster Whisper.
5. Faster Whisper transcribes the audio into text.
6. The text question goes through the same RAG, LLM, and TTS pipeline.
7. The frontend displays the transcript as the user message.
8. The frontend displays Aria's answer as text.
9. The audio answer auto-plays and remains available for replay.

## 8. Speech-to-Text

Speech-to-text is handled in:

```text
voice_agent/audio/speech_to_text.py
```

The project uses Faster Whisper. Faster Whisper is a fast implementation of OpenAI Whisper-style transcription. It converts the user's recorded audio into text.

The STT module:

- Accepts WAV bytes or NumPy audio.
- Writes temporary audio if needed.
- Runs transcription through the Whisper model.
- Cleans the result.
- Detects empty speech.
- Returns a structured `TranscriptionResult`.

The orchestrator only continues to RAG and LLM if speech was actually detected.

## 9. Text-to-Speech

Text-to-speech is handled in:

```text
voice_agent/audio/text_to_speech.py
```

The current working TTS engine is Piper running locally via the Piper CLI.

Important settings:

```python
PIPER_BINARY_PATH = "voice_agent/assets/piper/piper.exe"
PIPER_MODEL_PATH = "voice_agent/assets/voices/piper.onnx"
PIPER_CONFIG_PATH = "voice_agent/assets/voices/piper.onnx.json"
PIPER_SPEAKER_ID = 0
PIPER_LENGTH_SCALE = 1.0
```

The selected voice uses a local ONNX model. Piper is called per chunk to keep latency low.

The TTS flow works like this:

1. The LLM response is cleaned for speech.
2. Piper generates audio chunks locally.
3. The backend concatenates the chunks.
4. The WAV bytes are returned to the frontend.
5. The frontend embeds the WAV as a base64 audio URL.
6. The audio auto-plays once and can be replayed manually.

## 10. LLM and Prompting

The LLM layer lives in:

```text
voice_agent/llm/
```

Important files:

```text
voice_agent/llm/groq_client.py
voice_agent/llm/prompt_builder.py
voice_agent/llm/response_generator.py
```

The Groq client sends the final prompt to the configured Groq model. The prompt builder combines:

- System behavior instructions.
- Conversation history.
- Retrieved knowledge base context.
- The user's current question.

The response generator controls the answer flow. It can:

- Answer from session memory when the user asks about previous questions.
- Answer role/capability questions directly.
- Use RAG context for normal company questions.
- Return a safe fallback if the knowledge base does not contain the answer.

The system prompt is defined in:

```text
voice_agent/config/prompts.py
```

It has been tuned so Aria behaves like a customer clarification agent. Aria is instructed to sound natural, use short acknowledgements, ask gentle follow-up questions, and avoid overly rigid FAQ-style behavior.

## 11. Session Memory

Session memory is handled by:

```text
voice_agent/memory/conversation_memory.py
voice_agent/memory/history_manager.py
```

The system keeps a sliding window of recent conversation turns. This allows Aria to understand follow-up questions and answer memory-related questions.

Example:

```text
User: What services does CognitBotz offer?
Aria: CognitBotz offers...
User: What was my previous question?
Aria: Your previous question was: "What services does CognitBotz offer?"
```

Memory is stored for the current running session. When the user clears history or restarts the backend, the session memory resets.

## 12. Natural Conversation Behavior

The assistant is now designed to sound less robotic.

It can:

- Acknowledge the user naturally.
- Answer directly without unnecessary formality.
- Ask a short follow-up question after useful answers.
- Explain what it can help with.
- Clarify that it is a CognitBotz customer clarification agent.
- Avoid falling back incorrectly for questions about its own role.

For example, if the user asks:

```text
Ariya, do we know everything about the company?
```

The assistant now answers in a customer-facing way:

```text
Yes, I can help customers understand CognitBotz based on the company knowledge available to me. I can clarify services, AI solutions, automation capabilities, industries served, case studies, products, technologies, and contact details. If something is outside my current knowledge base, I will be transparent and guide you to the CognitBotz team for the exact details. What would you like to clarify about the company?
```

This is better than a rigid "I don't have specific information" fallback because the user is asking about the assistant's purpose, not a missing company fact.

## 13. Frontend UI

The modern frontend is in:

```text
frontend/
```

The UI has been redesigned into a clean black modern interface. It avoids gradients, neon styling, and overly "AI-looking" visuals.

Current UI characteristics:

- Black background.
- Clean typography.
- Minimal header.
- Simple message bubbles.
- Clear user and assistant labels.
- Voice and text input in one clean input bar.
- Audio player under assistant responses.
- Auto-play for newly generated assistant audio.
- Replay controls for listening again.
- Source cards for retrieved knowledge.
- Latency panel for response timing.
- Minimal icon usage.
- No gradient-heavy hero sections.
- No decorative bokeh, orbs, or visual clutter.

### Header

File:

```text
frontend/src/components/Header.tsx
```

The header shows:

- Project name: CognitBotz Voice AI.
- Subtitle: Enterprise AI knowledge assistant.
- Current message count.
- Clear conversation button.

### Chat Interface

File:

```text
frontend/src/components/ChatInterface.tsx
```

This component:

- Displays the empty welcome state.
- Renders all messages.
- Auto-scrolls to the newest message.
- Displays API or processing errors.
- Includes the input area at the bottom.

### Message Bubbles

File:

```text
frontend/src/components/ChatMessage.tsx
```

This component displays:

- User messages.
- Assistant messages.
- Assistant audio player.
- Source cards.
- Latency information.

User messages are visually distinct from Aria's messages.

### Input Area

File:

```text
frontend/src/components/InputArea.tsx
```

The input area supports:

- Typed questions.
- Microphone recording.
- Recording timer.
- Send button.
- Loading state.

Voice recording works through the browser's `MediaRecorder` API.

### Audio Player

File:

```text
frontend/src/components/AudioPlayer.tsx
```

The audio player:

- Receives base64 WAV audio.
- Builds a `data:audio/wav;base64,...` URL.
- Auto-plays once for new assistant responses.
- Allows pause and play.
- Allows replay after the audio finishes.
- Shows current time and duration.
- Provides a progress slider.

This means the user hears Aria automatically when the answer is generated, but can still listen again.

### Source Cards

File:

```text
frontend/src/components/SourceCards.tsx
```

Source cards show which knowledge base sections were used to answer the question. They can be expanded and collapsed.

They may show:

- Source title.
- Preview text.
- Match score.

### Latency Badge

File:

```text
frontend/src/components/LatencyBadge.tsx
```

This component shows timing information for:

- Speech recognition.
- Retrieval.
- LLM generation.
- Voice synthesis.
- Total response time.

## 14. Frontend State Management

The frontend state lives in:

```text
frontend/src/store/conversationStore.ts
```

It uses Zustand.

The store manages:

- Message list.
- Loading state.
- Error state.
- Sending typed messages.
- Sending audio messages.
- Clearing history.
- Loading previous session history from the backend.

When a typed message is sent:

1. The user message is immediately added to the UI.
2. Axios posts to `/api/chat/text`.
3. The backend returns Aria's text and audio.
4. The assistant message is added to the UI.
5. The audio player auto-plays.

When an audio message is sent:

1. The browser records audio.
2. The audio blob is posted to `/api/chat/audio`.
3. The backend transcribes it.
4. The user transcript is displayed.
5. Aria's text response is displayed.
6. The audio response auto-plays.

## 15. Step-by-Step Runtime Walkthrough

### Step 1: User Opens the Website

The user opens the Next.js frontend, usually at:

```text
http://localhost:3000
```

The UI loads the current conversation history from:

```text
GET http://localhost:8000/api/history
```

If there is no active conversation, the page shows the welcome state.

### Step 2: User Asks a Question

The user can either type a question or record audio.

Typed example:

```text
What services does CognitBotz offer?
```

Voice example:

```text
The user clicks the microphone, speaks, and stops recording.
```

### Step 3: Frontend Sends Request

For text:

```text
POST /api/chat/text
```

For voice:

```text
POST /api/chat/audio
```

### Step 4: Backend Processes the Question

The backend orchestrator receives the request.

For audio, it first runs speech-to-text:

```text
audio -> Faster Whisper -> transcript
```

Then both text and voice questions continue through the same flow:

```text
transcript/query -> retrieval -> LLM -> TTS
```

### Step 5: Retrieval Finds Knowledge

The retriever searches FAISS for chunks that match the question.

The result contains:

- Matching documents.
- Similarity scores.
- Context text.
- Source labels.

### Step 6: Prompt Is Built

The prompt builder creates a message list containing:

- System prompt.
- Previous conversation history.
- Retrieved context.
- Current user question.

### Step 7: LLM Generates Text Answer

The Groq model generates a grounded answer. The response generator cleans it and prepares it for voice.

### Step 8: TTS Generates Audio

The cleaned answer is sent to the local XTTS-v2 model.

XTTS-v2 returns audio chunks. The backend concatenates them into WAV bytes.

### Step 9: API Returns Full Response

The API returns:

- Transcript.
- Text answer.
- Base64 WAV audio.
- Source cards.
- Latency metrics.

### Step 10: Frontend Displays and Plays

The frontend:

- Shows the user question.
- Shows Aria's text answer.
- Displays the audio player.
- Auto-plays the answer audio once.
- Allows replay.
- Shows source cards and latency information.

## 16. Configuration

Main backend config:

```text
voice_agent/config/settings.py
```

Main prompt config:

```text
voice_agent/config/prompts.py
```

Frontend API config:

```text
frontend/.env.local
```

Expected frontend environment value:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Backend environment file:

```text
voice_agent/.env
```

This should contain the Groq API key and other backend configuration values.

## 17. Running the Project

### Backend

From the project root:

```powershell
D:\projects\Cognitbotz-voice-agent\venv_py311\Scripts\Activate.ps1
cd D:\projects\Cognitbotz-voice-agent\voice_agent
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

Backend URL:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/api/health
```

### Frontend

From the project root:

```powershell
cd D:\projects\Cognitbotz-voice-agent\frontend
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

## 18. Testing

Backend tests are inside:

```text
voice_agent/tests/
```

Important tests:

```text
voice_agent/tests/test_tts.py
voice_agent/tests/test_pipeline.py
voice_agent/tests/test_memory.py
voice_agent/tests/test_rag.py
voice_agent/tests/test_stt.py
```

Run tests:

```powershell
cd D:\projects\Cognitbotz-voice-agent\voice_agent
D:\projects\Cognitbotz-voice-agent\venv_py311\Scripts\python.exe -m pytest tests -q
```

Frontend production build:

```powershell
cd D:\projects\Cognitbotz-voice-agent\frontend
npm run build
```

## 19. Key Improvements Made During Development

Several important fixes and improvements were made:

### Local TTS Migration

The TTS system was migrated to fully local XTTS-v2 to remove cloud dependency and reduce external latency variability. The model is preloaded on startup and runs on GPU when available.

### Chunked Synthesis

Long responses are split into sentence-sized chunks to keep synthesis responsive. Chunks are concatenated into one WAV stream for the frontend.

### Auto-Playback

The frontend now auto-plays new assistant audio responses once they arrive.

### Replay Support

The audio player remains visible after playback so the user can replay the response.

### Natural Conversation

The prompt was tuned so Aria:

- Acknowledges naturally.
- Asks useful follow-up questions.
- Behaves like a customer clarification agent.
- Does not use the fallback for role/capability questions.

### Session Memory

The assistant can now answer direct session-memory questions, such as:

```text
What was my previous question?
```

### Symbol Speech Fix

The TTS normalizer now expands:

```text
& -> and
+ -> plus
```

This makes voice output more natural for knowledge-base phrases like:

```text
AI & Automation
```

## 20. Current User Experience

The final user experience works like this:

1. User opens the website.
2. User asks a question by voice or text.
3. Aria responds with text.
4. Aria automatically speaks the answer.
5. The user can replay the audio.
6. The user can ask follow-up questions.
7. Aria remembers the current session.
8. The UI stays clean, modern, black-themed, and minimal.

This creates a more complete customer-facing AI assistant experience, not just a text chatbot.

## 21. Future Improvement Ideas

Possible future enhancements:

- Add per-user persistent memory using a database.
- Add authentication for internal/admin usage.
- Add an admin page for updating the knowledge base.
- Add live streaming responses.
- Add streaming TTS for faster first audio playback.
- Add voice interruption and barge-in.
- Add multilingual support.
- Add CRM lead capture.
- Add analytics for most asked questions.
- Add feedback buttons for answer quality.
- Add deployment configuration for cloud hosting.

## 22. Summary

The CognitBotz Voice AI Consultant is a complete voice-enabled RAG assistant. It combines a modern frontend, a FastAPI backend, speech-to-text, vector search, LLM generation, text-to-speech, session memory, and a polished black UI.

It is built to help customers clarify what CognitBotz does, understand services and AI solutions, ask natural follow-up questions, and receive both written and spoken answers.

The project demonstrates a strong end-to-end AI application architecture: browser voice input, backend intelligence pipeline, grounded knowledge retrieval, human-like conversational response generation, voice synthesis, automatic audio playback, and clean frontend presentation.
