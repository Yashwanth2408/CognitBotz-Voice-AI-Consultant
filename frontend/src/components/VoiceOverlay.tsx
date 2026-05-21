"use client"

import React, { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Mic, X } from "lucide-react"

interface VoiceOverlayProps {
  isVisible: boolean
  onClose: () => void
}

const VoiceOverlay: React.FC<VoiceOverlayProps> = ({ isVisible, onClose }) => {
  const [voiceBars, setVoiceBars] = useState<number[]>([])

  // Generate animated voice bars
  useEffect(() => {
    setVoiceBars(Array.from({ length: 7 }, () => Math.random()))
  }, [])

  if (!isVisible) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-xl rounded-[52px]"
    >
      <div className="flex flex-col items-center justify-center gap-8">
        {/* Animated orb with glow */}
        <div className="relative">
          {/* Outer halos */}
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="absolute inset-0 rounded-full"
            style={{
              width: "140px",
              height: "140px",
              boxShadow: "0 0 40px rgba(196, 181, 253, 0.2)",
            }}
          />

          <motion.div
            animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.1, 0.3] }}
            transition={{ duration: 2.5, repeat: Infinity }}
            className="absolute inset-0 rounded-full border border-accent-mauve/30"
            style={{
              width: "140px",
              height: "140px",
            }}
          />

          {/* Main orb */}
          <motion.div
            animate={{
              boxShadow: [
                "0 0 40px rgba(196, 181, 253, 0.25), 0 0 80px rgba(196, 181, 253, 0.1)",
                "0 0 60px rgba(196, 181, 253, 0.35), 0 0 120px rgba(196, 181, 253, 0.2)",
                "0 0 40px rgba(196, 181, 253, 0.25), 0 0 80px rgba(196, 181, 253, 0.1)",
              ],
            }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-32 h-32 rounded-full bg-dark-card border border-accent-mauve/40 flex items-center justify-center"
          >
            <Mic size={56} className="text-accent-mauve" strokeWidth={1.5} />
          </motion.div>
        </div>

        {/* Listening label */}
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-white font-dm-sans">Listening…</h2>
        </div>

        {/* Animated voice bars */}
        <div className="flex items-center justify-center gap-1.5 h-12">
          {voiceBars.map((_, index) => (
            <motion.div
              key={index}
              animate={{
                height: ["6px", "28px", "6px"],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: index * 0.15,
                ease: "easeInOut",
              }}
              className="w-1 rounded-full bg-accent-mauve"
            />
          ))}
        </div>

        {/* Close button */}
        <motion.button
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.95 }}
          onClick={onClose}
          className="mt-8 flex items-center justify-center w-14 h-14 rounded-full bg-dark-surface border border-dark-border hover:border-dark-muted2 transition-colors"
        >
          <X size={24} className="text-dark-muted2" strokeWidth={2} />
        </motion.button>
      </div>
    </motion.div>
  )
}

export default VoiceOverlay
