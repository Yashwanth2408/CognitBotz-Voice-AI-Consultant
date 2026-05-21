"use client"

import { useRef, useEffect, useState } from "react"
import { Message, useConversationStore } from "@/store/conversationStore"
import ChatMessage from "./ChatMessage"
import InputArea from "./InputArea"
import ChatHeader from "./ChatHeader"
import VoiceOverlay from "./VoiceOverlay"
import { motion } from "framer-motion"

export default function ChatInterface() {
  const { messages, error, regenerateFromQuery, newSession, deleteSession } = useConversationStore()
  const [isVoiceOverlayOpen, setIsVoiceOverlayOpen] = useState(false)
  const [latency, setLatency] = useState(42)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Simulate latency updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLatency(Math.floor(Math.random() * 40) + 30)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleRegenerate = async (message: Message) => {
    if (message.role !== "assistant") return

    const queryFromMessage = message.user_query?.trim()
    if (queryFromMessage) {
      await regenerateFromQuery(queryFromMessage)
      return
    }

    const assistantIndex = messages.findIndex((m) => m.id === message.id)
    if (assistantIndex <= 0) return

    for (let i = assistantIndex - 1; i >= 0; i -= 1) {
      if (messages[i].role === "user") {
        await regenerateFromQuery(messages[i].text)
        return
      }
    }
  }

  return (
    <div className="h-screen bg-primary-dark flex items-center justify-center p-4">
      {/* Phone frame container */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md h-full max-h-screen flex flex-col rounded-[52px] border border-dark-border overflow-hidden shadow-2xl"
        style={{
          backgroundColor: "#0b0b0f",
          boxShadow:
            "0 0 60px rgba(196, 181, 253, 0.06), 0 20px 60px rgba(0, 0, 0, 0.55)",
        }}
      >
        {/* Header */}
        <ChatHeader
          onBack={() => console.log("Back")}
          onEdit={() => console.log("Edit")}
          latency={latency}
        />

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 scrollbar-thin scrollbar-track-dark-main scrollbar-thumb-dark-border hover:scrollbar-thumb-accent-mauve">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-4">
                <div className="mx-auto w-16 h-16 rounded-full bg-accent-mauve/10 border border-accent-mauve/30 flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-accent-mauve"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-white">Welcome to Aria</h2>
                <p className="text-sm text-dark-muted max-w-xs">
                  Ask questions about CognitBotz by voice or text. Aria will answer and remember your session.
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Date divider */}
              <div className="flex items-center gap-3 py-4">
                <div className="flex-1 h-px bg-dark-border" />
                <span className="text-xs text-dark-muted font-medium">Today</span>
                <div className="flex-1 h-px bg-dark-border" />
              </div>

              {/* Messages */}
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  onRegenerate={handleRegenerate}
                />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}

          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 p-4 bg-dark-card border border-accent-border rounded-2xl"
            >
              <p className="text-sm text-accent-mauve">{error}</p>
            </motion.div>
          )}
        </div>

        {/* Input area */}
        <InputArea
          onNewSession={newSession}
          onDeleteSession={deleteSession}
        />

        {/* Voice overlay */}
        <VoiceOverlay
          isVisible={isVoiceOverlayOpen}
          onClose={() => setIsVoiceOverlayOpen(false)}
        />
      </motion.div>
    </div>
  )
}
