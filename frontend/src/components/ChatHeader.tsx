"use client"

import React from "react"
import { ArrowLeft, Edit3 } from "lucide-react"
import { motion } from "framer-motion"

interface ChatHeaderProps {
  onBack?: () => void
  onEdit?: () => void
  latency?: number
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  onBack,
  onEdit,
  latency = 42,
}) => {
  return (
    <div className="w-full border-b border-dark-border pb-4">
      {/* Top navigation bar */}
      <div className="flex items-center justify-between px-4 pt-4">
        {/* Back button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onBack}
          className="flex items-center justify-center w-10 h-10 rounded-full bg-dark-surface border border-dark-border hover:border-accent-mauve/50 transition-colors"
        >
          <ArrowLeft size={20} className="text-white" />
        </motion.button>

        {/* Title */}
        <h1 className="text-nav-title text-white font-dm-sans font-semibold tracking-tight">
          Chat – Axel Pro
        </h1>

        {/* Edit button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onEdit}
          className="flex items-center justify-center w-10 h-10 rounded-full bg-accent-mauve hover:bg-accent-mauve/90 transition-colors"
        >
          <Edit3 size={20} className="text-black" strokeWidth={2} />
        </motion.button>
      </div>

      {/* Status pill */}
      <div className="flex items-center justify-center mt-4">
        <motion.div
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-dark-surface border border-dark-border"
        >
          {/* Pulsing dot */}
          <motion.div
            animate={{ opacity: [1, 0.4] }}
            transition={{ duration: 1.8, repeat: Infinity }}
            className="w-2 h-2 rounded-full bg-accent-mauve"
          />

          {/* Latency in monospace */}
          <span className="font-dm-mono text-sm font-medium text-white tracking-tighter">
            {latency}ms
          </span>

          {/* Online status */}
          <span className="text-xs text-dark-muted">· online</span>
        </motion.div>
      </div>
    </div>
  )
}

export default ChatHeader
