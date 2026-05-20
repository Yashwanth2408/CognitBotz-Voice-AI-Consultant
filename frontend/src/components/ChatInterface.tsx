"use client"

import { useRef, useEffect } from "react"
import { useConversationStore } from "@/store/conversationStore"
import ChatMessage from "./ChatMessage"
import InputArea from "./InputArea"

export default function ChatInterface() {
  const { messages, error } = useConversationStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-dark-bg">
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto w-full px-4 py-8">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full py-20">
              <div className="text-center max-w-md">
                <div className="mx-auto mb-6 h-12 w-12 rounded-full border border-dark-border bg-dark-surface" />
                <h2 className="text-2xl font-semibold tracking-tight text-dark-text mb-3">
                  Welcome to CognitBotz
                </h2>
                <p className="text-dark-muted leading-relaxed">
                  Ask by voice or text. Aria will answer with text and speech, and remember this session.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}

          {error && (
            <div className="mt-4 p-4 bg-red-950/20 border border-accent-danger text-red-200 rounded-md">
              {error}
            </div>
          )}
        </div>
      </div>

      <InputArea />
    </div>
  )
}
