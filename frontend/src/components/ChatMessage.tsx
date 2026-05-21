"use client"

import { Message } from "@/store/conversationStore"
import AudioPlayer from "./AudioPlayer"
import LatencyBadge from "./LatencyBadge"
import SourceCards from "./SourceCards"
import { motion } from "framer-motion"
import { Sparkles, User, Copy, RotateCcw, Volume2 } from "lucide-react"
import { useState } from "react"

interface ChatMessageProps {
  message: Message
  onRegenerate?: (message: Message) => void
}

export default function ChatMessage({ message, onRegenerate }: ChatMessageProps) {
  const isUser = message.role === "user"
  const [replayNonce, setReplayNonce] = useState(0)

  const copyMessage = async () => {
    try {
      await navigator.clipboard.writeText(message.text)
    } catch {
      // Ignore clipboard failures in unsupported contexts.
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-3 mb-6 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center flex-col-reverse ${
          isUser
            ? "bg-gradient-to-br from-accent-user_from to-accent-user_to"
            : "bg-dark-card border border-dark-border"
        }`}
      >
        {isUser ? (
          <User size={16} className="text-white" strokeWidth={2} />
        ) : (
          <Sparkles size={16} className="text-accent-mauve" strokeWidth={2} />
        )}
      </div>

      {/* Message content */}
      <div className={`flex flex-col gap-2 max-w-md ${isUser ? "items-end" : "items-start"}`}>
        {/* AI label */}
        {!isUser && (
          <span className="text-label text-dark-muted2 px-3 pt-1">Aria</span>
        )}

        {/* Message bubble */}
        <motion.div
          className={`px-6 py-3 border text-body text-white ${
            isUser
              ? "bg-gradient-to-r from-accent-user_from to-accent-user_to border-transparent rounded-[24px_24px_6px_24px]"
              : "bg-[#23232c] border-dark-border rounded-[6px_24px_24px_24px]"
          }`}
        >
          <p className="leading-relaxed break-words whitespace-pre-wrap">
            {message.text}
          </p>
        </motion.div>

        {!isUser && (
          <div className="pl-2 flex items-center gap-2">
            <button
              type="button"
              onClick={copyMessage}
              className="inline-flex items-center gap-1 rounded-full border border-dark-border bg-dark-input px-2 py-1 text-[11px] text-dark-muted2 hover:text-white"
            >
              <Copy size={12} />
              Copy
            </button>
            <button
              type="button"
              onClick={() => setReplayNonce((v) => v + 1)}
              disabled={!message.audio_bytes_b64}
              className="inline-flex items-center gap-1 rounded-full border border-dark-border bg-dark-input px-2 py-1 text-[11px] text-dark-muted2 hover:text-white"
            >
              <Volume2 size={12} />
              Replay
            </button>
            <button
              type="button"
              onClick={() => onRegenerate?.(message)}
              className="inline-flex items-center gap-1 rounded-full border border-dark-border bg-dark-input px-2 py-1 text-[11px] text-dark-muted2 hover:text-white"
            >
              <RotateCcw size={12} />
              Regenerate
            </button>
          </div>
        )}

        {/* AI extras: audio, sources, latency */}
        {!isUser && (
          <div className="flex flex-col gap-3 w-full mt-2">
            {message.audio_bytes_b64 && (
              <div className="pl-3">
                <AudioPlayer
                  audioBase64={message.audio_bytes_b64}
                  autoPlay={message.autoPlay === true}
                  replayNonce={replayNonce}
                />
              </div>
            )}

            {message.source_cards && message.source_cards.length > 0 && (
              <div className="pl-3">
                <SourceCards sources={message.source_cards} />
              </div>
            )}

            {message.latency && (
              <div className="pl-3">
                <LatencyBadge latency={message.latency} />
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}
