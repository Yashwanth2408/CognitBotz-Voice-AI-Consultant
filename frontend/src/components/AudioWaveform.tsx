"use client"

import React, { useRef, useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Play, Pause } from "lucide-react"

interface AudioWaveformProps {
  audioBase64: string
  duration?: number
  autoPlay?: boolean
}

const AudioWaveform: React.FC<AudioWaveformProps> = ({
  audioBase64,
  duration = 30,
  autoPlay = false,
}) => {
  const audioRef = useRef<HTMLAudioElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [waveformData, setWaveformData] = useState<number[]>([])

  // Generate waveform data (36 bars)
  useEffect(() => {
    const bars = Array.from({ length: 36 }, () =>
      Math.random() * 0.8 + 0.2
    )
    setWaveformData(bars)
  }, [])

  // Draw waveform on canvas
  useEffect(() => {
    if (!canvasRef.current || waveformData.length === 0) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    canvas.width = canvas.offsetWidth * window.devicePixelRatio
    canvas.height = canvas.offsetHeight * window.devicePixelRatio
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

    const barWidth = 3
    const gap = 2
    const barHeight = canvas.offsetHeight

    waveformData.forEach((value, index) => {
      const x = index * (barWidth + gap)
      const height = barHeight * value
      const y = barHeight / 2 - height / 2

      // Filled/unfilled based on progress
      const fillRatio = currentTime / duration
      const isFilled = index / waveformData.length < fillRatio

      // Draw bar
      ctx.fillStyle = isFilled ? "#c4b5fd" : "#2a2a33"
      ctx.strokeStyle = "transparent"

      // Bar with rounded corners
      ctx.beginPath()
      ctx.moveTo(x, y + 2)
      ctx.lineTo(x, y + height - 2)
      ctx.lineWidth = barWidth
      ctx.stroke()
      ctx.fillRect(x, y + 2, barWidth, Math.max(height - 4, 1))
    })
  }, [waveformData, currentTime, duration])

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause()
      } else {
        audioRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime)
    }
  }

  const handleEnded = () => {
    setIsPlaying(false)
    setCurrentTime(0)
  }

  const formatTime = (time: number) => {
    const mins = Math.floor(time / 60)
    const secs = Math.floor(time % 60)
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-dark-card border border-accent-border rounded-2xl">
      {/* Waveform canvas */}
      <div className="flex-1 h-12 bg-dark-input rounded-lg overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          style={{ display: "block" }}
        />
      </div>

      {/* Duration */}
      <span className="font-dm-mono text-sm text-dark-muted2 min-w-max">
        {formatTime(currentTime)}
      </span>

      {/* Play button */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={togglePlay}
        className="flex items-center justify-center w-9 h-9 rounded-full bg-accent-mauve hover:bg-accent-mauve/90 flex-shrink-0 transition-colors"
      >
        {isPlaying ? (
          <Pause size={18} className="text-black" strokeWidth={2} />
        ) : (
          <Play size={18} className="text-black ml-0.5" strokeWidth={2} />
        )}
      </motion.button>

      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={`data:audio/wav;base64,${audioBase64}`}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        autoPlay={autoPlay}
      />
    </div>
  )
}

export default AudioWaveform
