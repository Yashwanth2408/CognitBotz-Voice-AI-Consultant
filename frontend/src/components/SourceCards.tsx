"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"

interface SourceCard {
  title?: string
  content?: string
  source?: string
  preview?: string
  score_pct?: string
}

interface SourceCardsProps {
  sources: SourceCard[]
}

export default function SourceCards({ sources }: SourceCardsProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="rounded-md border border-dark-border bg-dark-bg p-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-sm font-medium text-dark-text hover:text-white transition-colors"
      >
        <span>Sources ({sources.length})</span>
        <ChevronDown
          size={16}
          className={`transition-transform text-dark-muted ${isExpanded ? "rotate-180" : ""}`}
        />
      </button>

      {isExpanded && (
        <div className="space-y-2 mt-3">
          {sources.map((source, idx) => (
            <div key={idx} className="border-t border-dark-border pt-2 text-xs">
              <div className="flex items-center justify-between gap-3">
                <h4 className="font-medium text-dark-text truncate">
                  {source.title || source.source || `Source ${idx + 1}`}
                </h4>
                {source.score_pct && <span className="text-dark-muted">{source.score_pct}</span>}
              </div>
              <p className="text-dark-muted mt-1 line-clamp-2">
                {source.content || source.preview || ""}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
