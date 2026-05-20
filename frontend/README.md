# CognitBotz Voice AI Frontend

Modern black-themed React/Next.js frontend for the CognitBotz Voice AI Consultant.

## 🎨 Features

- **Modern Design**: Dark theme with neon accents (black background with cyan/green highlights)
- **Real-time Chat**: Seamless text and voice conversations
- **Voice Recording**: Built-in microphone support for audio input
- **Audio Playback**: Integrated audio player for AI-generated responses
- **Response Metrics**: Visual breakdown of response latency (STT, Retrieval, LLM, TTS)
- **Source Attribution**: Collapsible cards showing KB sources used for the response
- **Session Management**: Conversation history with clear session option
- **Responsive Design**: Works on desktop and tablet
- **Smooth Animations**: Framer Motion animations for polished UX

## 🛠 Tech Stack

- **React 18** - UI library
- **Next.js 14** - Full-stack framework
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **Zustand** - State management
- **Axios** - HTTP client
- **Lucide React** - Icon library

## 📋 Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:8000`
- FastAPI server initialized

## 🚀 Installation

### 1. Install Dependencies

```bash
cd frontend
npm install
# or
yarn install
```

### 2. Configure Environment

```bash
cp .env.local.example .env.local
# Edit .env.local if your backend is on a different URL
```

### 3. Start Development Server

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   └── globals.css         # Global styles
│   ├── components/
│   │   ├── ChatInterface.tsx   # Main chat container
│   │   ├── ChatMessage.tsx     # Individual message bubble
│   │   ├── AudioPlayer.tsx     # Audio playback control
│   │   ├── InputArea.tsx       # Text/voice input
│   │   ├── Header.tsx          # Top navigation
│   │   ├── LatencyBadge.tsx   # Performance metrics
│   │   └── SourceCards.tsx    # KB source cards
│   └── store/
│       └── conversationStore.ts # Zustand state management
├── public/                     # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
└── next.config.js
```

## 🎯 Key Components

### ChatInterface
Main container managing message display and auto-scrolling.

### ChatMessage
Renders individual message bubbles with:
- Avatar badges
- Text content
- Audio player (for AI responses)
- Source cards
- Latency metrics

### InputArea
Text input with:
- Send button
- Voice recording toggle
- Recording timer
- Character counter

### AudioPlayer
Custom audio player with:
- Play/pause controls
- Progress bar
- Time display
- Volume indicator

## 🔌 API Integration

Frontend communicates with FastAPI backend via REST APIs:

### Text Chat
```
POST /api/chat/text
Body: { "text": "user query" }
```

### Audio Chat
```
POST /api/chat/audio
Body: multipart/form-data with audio file
```

### History
```
GET /api/history
POST /api/history/clear
```

## 🎨 Dark Theme Colors

- **Background**: `#0a0a0a` (pure black)
- **Surface**: `#1a1a1a` (dark gray)
- **Border**: `#2a2a2a` (subtle gray)
- **Text**: `#e5e5e5` (light gray)
- **Primary Accent**: `#00ff9f` (neon cyan)
- **Secondary Accent**: `#00d9ff` (bright cyan)

## 📱 Responsive Breakpoints

- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

## 🔧 Build for Production

```bash
npm run build
npm start
```

## 📝 License

Proprietary - CognitBotz
