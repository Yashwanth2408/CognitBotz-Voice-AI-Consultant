"use client"

import { useState, useEffect } from "react"
import ChatInterface from "@/components/ChatInterface"
import Header from "@/components/Header"
import { useConversationStore } from "@/store/conversationStore"

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
      <div className="flex items-center justify-center min-h-screen bg-dark-bg">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-dark-text mx-auto mb-4"></div>
          <p className="text-dark-muted">Loading workspace...</p>
        </div>
      </div>
    )
  }

  return (
    <main className="flex flex-col h-screen bg-dark-bg overflow-hidden">
      <Header />
      <ChatInterface />
    </main>
  )
}
