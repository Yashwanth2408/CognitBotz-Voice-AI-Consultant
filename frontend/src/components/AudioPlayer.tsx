"use client"

import { useRef, useState, useEffect } from "react"
import { Play, Pause, Volume2 } from "lucide-react"

interface AudioPlayerProps {
  audioBase64: string
  autoPlay?: boolean
  replayNonce?: number
}

export default function AudioPlayer({
  audioBase64,
  autoPlay = false,
  replayNonce = 0,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const hasAutoPlayedRef = useRef(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [bars, setBars] = useState<number[]>([])
  const audioUrl = `data:audio/wav;base64,${audioBase64}`

  useEffect(() => {
    const nextBars = Array.from({ length: 36 }, (_, idx) => {
      const v = Math.abs(Math.sin((idx + 1) * 1.31))
      return 0.2 + v * 0.8
    })
    setBars(nextBars)
  }, [audioBase64])

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

  useEffect(() => {
    const audio = audioRef.current
    if (!audio || replayNonce === 0) return
    audio.currentTime = 0
    setCurrentTime(0)
    audio.play()
      .then(() => setIsPlaying(true))
      .catch(() => setIsPlaying(false))
  }, [replayNonce])

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

  const formatTime = (time: number) => {
    if (!time || isNaN(time)) return "0:00"
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, "0")}`
  }

  const progressRatio = duration > 0 ? Math.min(currentTime / duration, 1) : 0

  return (
    <div className="flex items-center gap-3 bg-dark-card rounded-2xl p-3 border border-dark-border">
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      <button
        onClick={togglePlay}
        className="flex-shrink-0 p-2 rounded-full bg-dark-input hover:bg-dark-border text-white transition-colors border border-dark-border"
        aria-label={isPlaying ? "Pause response audio" : "Play response audio"}
      >
        {isPlaying ? <Pause size={17} /> : <Play size={17} />}
      </button>

      <div className="flex-1 h-10 px-2">
        <div className="h-full flex items-end gap-[2px]">
          {bars.map((bar, index) => {
            const isFilled = index / bars.length <= progressRatio
            return (
              <span
                key={index}
                className={`w-[3px] rounded-sm ${isFilled ? "bg-accent-mauve" : "bg-dark-border"}`}
                style={{ height: `${Math.max(20, bar * 100)}%` }}
              />
            )
          })}
        </div>
      </div>

      <div className="text-xs text-dark-muted tabular-nums min-w-20 text-right">
        {formatTime(Math.max(duration - currentTime, 0))}
      </div>

      <Volume2 size={15} className="text-dark-muted" />
    </div>
  )
}
