"use client"

import { useRef, useState, useEffect } from "react"
import { Play, Pause, Volume2 } from "lucide-react"

interface AudioPlayerProps {
  audioBase64: string
  autoPlay?: boolean
}

export default function AudioPlayer({ audioBase64, autoPlay = false }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const hasAutoPlayedRef = useRef(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const audioUrl = `data:audio/wav;base64,${audioBase64}`

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const updateDuration = () => setDuration(Number.isFinite(audio.duration) ? audio.duration : 0)
    const updateTime = () => setCurrentTime(audio.currentTime)
    const handleEnded = () => {
      setIsPlaying(false)
      setCurrentTime(audio.duration || 0)
    }

    audio.addEventListener("loadedmetadata", updateDuration)
    audio.addEventListener("timeupdate", updateTime)
    audio.addEventListener("ended", handleEnded)

    return () => {
      audio.removeEventListener("loadedmetadata", updateDuration)
      audio.removeEventListener("timeupdate", updateTime)
      audio.removeEventListener("ended", handleEnded)
    }
  }, [audioBase64])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio || !autoPlay || hasAutoPlayedRef.current) return

    hasAutoPlayedRef.current = true
    audio.currentTime = 0
    audio.play()
      .then(() => setIsPlaying(true))
      .catch(() => {
        setIsPlaying(false)
      })
  }, [autoPlay, audioBase64])

  const togglePlay = async () => {
    const audio = audioRef.current
    if (!audio) return

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
      return
    }

    if (audio.ended || audio.currentTime >= audio.duration) {
      audio.currentTime = 0
      setCurrentTime(0)
    }

    await audio.play()
    setIsPlaying(true)
  }

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value)
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = time
    setCurrentTime(time)
  }

  const formatTime = (time: number) => {
    if (!time || isNaN(time)) return "0:00"
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, "0")}`
  }

  return (
    <div className="flex items-center gap-3 bg-dark-bg rounded-md p-3 border border-dark-border">
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      <button
        onClick={togglePlay}
        className="flex-shrink-0 p-2 rounded-md bg-dark-panel hover:bg-dark-border text-dark-text transition-colors"
        aria-label={isPlaying ? "Pause response audio" : "Play response audio"}
      >
        {isPlaying ? <Pause size={17} /> : <Play size={17} />}
      </button>

      <div className="text-xs text-dark-muted tabular-nums min-w-10">
        {formatTime(currentTime)}
      </div>

      <input
        type="range"
        min="0"
        max={duration || 0}
        value={currentTime}
        onChange={handleProgressChange}
        className="flex-1 h-1 bg-dark-border rounded-lg appearance-none cursor-pointer accent-white"
      />

      <div className="text-xs text-dark-muted tabular-nums min-w-10 text-right">
        {formatTime(duration)}
      </div>

      <Volume2 size={15} className="text-dark-muted" />
    </div>
  )
}
