"use client"

import { useState, useEffect } from "react"
import ChatInterface from "@/components/ChatInterface"
import { useConversationStore } from "@/store/conversationStore"
import { motion } from "framer-motion"

export default function Home() {
  const [isLoading, setIsLoading] = useState(true)
  const { initialize } = useConversationStore()

  useEffect(() => {
    // Initialize store and load history
    const init = async () => {
      await initialize()
      setIsLoading(false)
    }
    init()
  }, [initialize])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-primary-dark">
        <div className="text-center space-y-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="inline-block"
          >
            <div className="w-12 h-12 rounded-full border-2 border-dark-border border-t-accent-mauve" />
          </motion.div>
          <p className="text-dark-muted text-sm">Initializing Aria...</p>
        </div>
      </div>
    )
  }

  return (
    <ChatInterface />
  )
}
