"use client"

import React, { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { TrendingUp, ArrowUpRight } from "lucide-react"

interface DataAnalysisCardProps {
  title?: string
  subtitle?: string
  metricValue?: string
  percentChange?: number
  progress?: number
  tags?: string[]
  onExpand?: () => void
}

const DataAnalysisCard: React.FC<DataAnalysisCardProps> = ({
  title = "Data Analyze",
  subtitle = "Platform Engagement",
  metricValue = "2.4M",
  percentChange = 18.7,
  progress = 72,
  tags = ["Modern", "Minimalist", "Brutal"],
  onExpand,
}) => {
  const [displayProgress, setDisplayProgress] = useState(0)

  // Animate progress bar on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setDisplayProgress(progress)
    }, 100)
    return () => clearTimeout(timer)
  }, [progress])

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full bg-dark-card border border-dark-border rounded-3xl p-5 space-y-4"
    >
      {/* Header row */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-body font-semibold text-white">{title}</h3>
          <p className="text-xs text-dark-muted mt-1">{subtitle}</p>
        </div>

        {/* Expand button */}
        <motion.button
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.95 }}
          onClick={onExpand}
          className="flex items-center justify-center w-7 h-7 rounded-lg bg-dark-input border border-dark-border hover:border-accent-mauve/50 transition-colors"
        >
          <ArrowUpRight size={16} className="text-dark-muted2" strokeWidth={2} />
        </motion.button>
      </div>

      {/* Metric + badge row */}
      <div className="flex items-baseline gap-3">
        <h2 className="text-metric font-semibold text-white">{metricValue}</h2>

        {/* Percentage badge */}
        <div className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-dark-input border border-dark-border">
          <span className="font-dm-mono text-sm font-semibold text-accent-mauve">
            +{percentChange.toFixed(1)}%
          </span>
          <TrendingUp size={14} className="text-accent-mauve" strokeWidth={2} />
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="h-1.5 w-full bg-dark-input rounded-full overflow-hidden border border-dark-border">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${displayProgress}%` }}
            transition={{
              duration: 0.8,
              ease: [0.25, 0.46, 0.45, 0.94],
            }}
            className="h-full bg-accent-mauve rounded-full"
          />
        </div>
      </div>

      {/* Tags row */}
      <div className="flex gap-2 pt-2">
        {tags.map((tag, index) => (
          <div
            key={tag}
            className="inline-flex items-center gap-2 px-2 py-1 text-xs text-dark-muted2"
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{
                backgroundColor: [
                  "#f9a8d4",
                  "#c4b5fd",
                  "#8e8ea0",
                ][index % 3],
              }}
            />
            {tag}
          </div>
        ))}
      </div>
    </motion.div>
  )
}

export default DataAnalysisCard
