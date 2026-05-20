"use client"

import { Message } from "@/store/conversationStore"
import AudioPlayer from "./AudioPlayer"
import LatencyBadge from "./LatencyBadge"
import SourceCards from "./SourceCards"
import { motion } from "framer-motion"

interface ChatMessageProps {
  message: Message
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-2xl rounded-lg border px-4 py-3 ${
          isUser
            ? "bg-dark-text text-dark-bg border-dark-text"
            : "bg-dark-surface text-dark-text border-dark-border"
        }`}
      >
        <div className="flex items-start gap-3">
          <div
            className={`mt-1 h-7 w-7 rounded-full border flex-shrink-0 ${
              isUser
                ? "bg-dark-bg border-dark-bg"
                : "bg-dark-panel border-dark-border"
            }`}
          />

          <div className="flex-1 min-w-0">
            <div className={`text-xs font-medium mb-1 ${isUser ? "text-black/60" : "text-dark-muted"}`}>
              {isUser ? "You" : "Aria"}
            </div>

            <p className="leading-relaxed break-words whitespace-pre-wrap">
              {message.text}
            </p>

            {!isUser && message.audio_bytes_b64 && (
              <div className="mt-4">
                <AudioPlayer
                  audioBase64={message.audio_bytes_b64}
                  autoPlay={message.autoPlay === true}
                />
              </div>
            )}

            {!isUser && message.source_cards && message.source_cards.length > 0 && (
              <div className="mt-4">
                <SourceCards sources={message.source_cards} />
              </div>
            )}

            {!isUser && message.latency && (
              <div className="mt-4">
                <LatencyBadge latency={message.latency} />
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
