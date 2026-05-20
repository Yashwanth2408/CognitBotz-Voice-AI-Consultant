import { create } from "zustand"
import axios from "axios"

export interface Message {
  id: string
  role: "user" | "assistant"
  text: string
  audio_bytes_b64?: string
  autoPlay?: boolean
  timestamp: string
  latency?: {
    stt_ms: number
    retrieval_ms: number
    llm_ms: number
    tts_ms: number
    total_ms: number
  }
  source_cards?: Array<{
    title?: string
    content?: string
    source?: string
    preview?: string
    score_pct?: string
  }>
}

interface ConversationStore {
  messages: Message[]
  isLoading: boolean
  error: string | null
  
  // Actions
  addMessage: (message: Message) => void
  sendTextMessage: (text: string) => Promise<void>
  sendAudioMessage: (audioBlob: Blob) => Promise<void>
  clearHistory: () => Promise<void>
  initialize: () => Promise<void>
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const useConversationStore = create<ConversationStore>((set) => ({
  messages: [],
  isLoading: false,
  error: null,

  addMessage: (message: Message) => {
    set((state) => ({
      messages: [...state.messages, message],
    }))
  },

  sendTextMessage: async (text: string) => {
    const trimmedText = text.trim()
    if (!trimmedText) return

    set({ isLoading: true, error: null })

    try {
      // Add user message
      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        text: trimmedText,
        timestamp: new Date().toISOString(),
      }
      set((state) => ({
        messages: [...state.messages, userMessage],
      }))

      // Send to API
      const response = await axios.post(`${API_BASE}/api/chat/text`, {
        text: trimmedText,
      })

      if (response.data.success) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          text: response.data.response_text,
          audio_bytes_b64: response.data.audio_bytes_b64,
          autoPlay: true,
          timestamp: new Date().toISOString(),
          latency: response.data.latency,
          source_cards: response.data.source_cards,
        }
        set((state) => ({
          messages: [...state.messages, assistantMessage],
        }))
      } else {
        set({ error: response.data.error || "Failed to process request" })
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error"
      set({ error: `Error: ${message}` })
      console.error("Error sending message:", error)
    } finally {
      set({ isLoading: false })
    }
  },

  sendAudioMessage: async (audioBlob: Blob) => {
    set({ isLoading: true, error: null })

    try {
      const formData = new FormData()
      formData.append("audio_file", audioBlob, "audio.wav")

      const response = await axios.post(`${API_BASE}/api/chat/audio`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      })

      if (response.data.success) {
        // Add user message with transcript
        const userMessage: Message = {
          id: Date.now().toString(),
          role: "user",
          text: response.data.transcript,
          timestamp: new Date().toISOString(),
        }
        set((state) => ({
          messages: [...state.messages, userMessage],
        }))

        // Add assistant message
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          text: response.data.response_text,
          audio_bytes_b64: response.data.audio_bytes_b64,
          autoPlay: true,
          timestamp: new Date().toISOString(),
          latency: response.data.latency,
          source_cards: response.data.source_cards,
        }
        set((state) => ({
          messages: [...state.messages, assistantMessage],
        }))
      } else {
        set({ error: response.data.error || "Failed to process audio" })
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error"
      set({ error: `Error: ${message}` })
      console.error("Error sending audio:", error)
    } finally {
      set({ isLoading: false })
    }
  },

  clearHistory: async () => {
    try {
      await axios.post(`${API_BASE}/api/history/clear`)
      set({ messages: [] })
    } catch (error) {
      console.error("Error clearing history:", error)
    }
  },

  initialize: async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/history`)
      if (response.data.success && response.data.messages) {
        const messages: Message[] = response.data.messages.map(
          (msg: any, idx: number) => ({
            id: idx.toString(),
            role: msg.role,
            text: msg.text,
            audio_bytes_b64: msg.audio_bytes_b64,
            autoPlay: false,
            timestamp: msg.timestamp,
          })
        )
        set({ messages })
      }
    } catch (error) {
      console.error("Error initializing history:", error)
      // Continue without history
    }
  },
}))
