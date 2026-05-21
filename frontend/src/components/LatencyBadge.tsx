"use client"

import { Clock } from "lucide-react"

interface LatencyBadgeProps {
  latency: {
    stt_ms: number
    retrieval_ms: number
    llm_ms: number
    tts_ms: number
    total_ms: number
  }
}

export default function LatencyBadge({ latency }: LatencyBadgeProps) {
  const total = Math.max(latency.total_ms, 1)
  const segments = [
    { key: "stt", label: "Speech", value: latency.stt_ms, color: "bg-[#f9a8d4]" },
    { key: "ret", label: "Retrieval", value: latency.retrieval_ms, color: "bg-[#c4b5fd]" },
    { key: "llm", label: "Generation", value: latency.llm_ms, color: "bg-[#a5b4fc]" },
    { key: "tts", label: "Voice", value: latency.tts_ms, color: "bg-[#818cf8]" },
  ].filter((s) => s.value > 0)

  return (
    <div className="rounded-md border border-dark-border bg-dark-bg p-3">
      <div className="flex items-center gap-2 text-xs text-dark-muted mb-2">
        <Clock size={13} />
        <span>Response timing</span>
      </div>

      <div className="mb-3">
        <div className="h-2 w-full overflow-hidden rounded-full bg-dark-input border border-dark-border flex">
          {segments.map((segment) => (
            <div
              key={segment.key}
              className={`${segment.color} h-full`}
              style={{ width: `${(segment.value / total) * 100}%` }}
              title={`${segment.label}: ${segment.value}ms`}
            />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs text-dark-muted">
        {latency.stt_ms > 0 && <Metric label="Speech" value={latency.stt_ms} />}
        {latency.retrieval_ms > 0 && <Metric label="Retrieval" value={latency.retrieval_ms} />}
        {latency.llm_ms > 0 && <Metric label="Generation" value={latency.llm_ms} />}
        {latency.tts_ms > 0 && <Metric label="Voice" value={latency.tts_ms} />}
        <div className="col-span-2 flex justify-between border-t border-dark-border pt-2 text-dark-text">
          <span>Total</span>
          <span className="font-mono tabular-nums">{latency.total_ms}ms</span>
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between">
      <span>{label}</span>
      <span className="font-mono tabular-nums text-dark-text">{value}ms</span>
    </div>
  )
}
