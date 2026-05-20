"use client"

import { useConversationStore } from "@/store/conversationStore"
import { Trash2 } from "lucide-react"

export default function Header() {
  const { messages, clearHistory } = useConversationStore()

  const handleClearHistory = async () => {
    if (confirm("Clear the current conversation?")) {
      await clearHistory()
    }
  }

  return (
    <header className="border-b border-dark-border bg-dark-bg">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-dark-text">
            CognitBotz Voice AI
          </h1>
          <p className="text-sm text-dark-muted mt-1">Enterprise AI knowledge assistant</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-sm font-medium text-dark-text">{messages.length} messages</p>
            <p className="text-xs text-dark-muted">this session</p>
          </div>

          <button
            onClick={handleClearHistory}
            className="p-2 rounded-md border border-dark-border hover:bg-dark-panel text-dark-muted hover:text-dark-text transition-colors"
            title="Clear conversation"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>
    </header>
  )
}
