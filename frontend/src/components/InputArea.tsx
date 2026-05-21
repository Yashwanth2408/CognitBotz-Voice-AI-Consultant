"use client"

import { useState, useRef } from "react"
import { useConversationStore } from "@/store/conversationStore"
import { Send, Mic, PlusCircle, Trash2 } from "lucide-react"
import { motion } from "framer-motion"

interface InputAreaProps {
  onNewSession?: () => void
  onDeleteSession?: () => void
}

export default function InputArea({ onNewSession, onDeleteSession }: InputAreaProps) {
  const { sendTextMessage, sendAudioMessage, isLoading } = useConversationStore()
  const [text, setText] = useState("")
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data)
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" })
        await sendAudioMessage(audioBlob)
        setRecordingTime(0)
      }

      mediaRecorder.start()
      setIsRecording(true)

      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1)
      }, 1000)
    } catch (error) {
      console.error("Error accessing microphone:", error)
      alert("Could not access microphone. Please check permissions.")
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop())
      setIsRecording(false)
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current)
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (text.trim() && !isLoading) {
      await sendTextMessage(text)
      setText("")
    }
  }

  return (
    <div className="w-full border-t border-dark-border bg-primary-dark p-4 flex flex-col gap-3">
      {/* Main input pill */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 rounded-full border border-accent-border bg-dark-input px-4 py-2.5 transition-all focus-within:border-accent-mauve/50"
      >
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            isRecording
              ? `Recording ${Math.floor(recordingTime / 60)
                  .toString()
                  .padStart(2, "0")}:${(recordingTime % 60)
                  .toString()
                  .padStart(2, "0")}`
              : "Type a message or speak…"
          }
          disabled={isLoading || isRecording}
          className="flex-1 bg-transparent text-white placeholder-dark-muted focus:outline-none text-body disabled:opacity-50"
        />

        {/* Mic button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isLoading}
          className={`flex items-center justify-center w-9 h-9 rounded-full transition-all flex-shrink-0 ${
            isRecording
              ? "bg-dark-input border border-dark-border animate-pulse"
              : "bg-dark-input border border-dark-border hover:border-accent-mauve/40"
          }`}
        >
          <Mic
            size={18}
            className={isRecording ? "text-accent-mauve" : "text-dark-muted2"}
            strokeWidth={2}
          />
        </motion.button>

        {/* Send button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          type="submit"
          disabled={isLoading || !text.trim() || isRecording}
          className="flex items-center justify-center w-9 h-9 rounded-full bg-accent-mauve hover:bg-accent-mauve/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
        >
          {isLoading ? (
            <div className="w-4 h-4 rounded-full border-2 border-black border-t-transparent animate-spin" />
          ) : (
            <Send size={18} className="text-black" strokeWidth={2} />
          )}
        </motion.button>
      </form>

      {/* Session controls */}
      <div className="flex justify-start gap-2 px-1">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="button"
          onClick={onNewSession}
          className="inline-flex items-center gap-1.5 rounded-full border border-dark-border bg-dark-input px-3 py-1.5 text-xs text-dark-muted2 hover:text-white"
          title="Start new session"
        >
          <PlusCircle size={14} />
          New Session
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="button"
          onClick={onDeleteSession}
          className="inline-flex items-center gap-1.5 rounded-full border border-dark-border bg-dark-input px-3 py-1.5 text-xs text-dark-muted2 hover:text-white"
          title="Delete current session"
        >
          <Trash2 size={14} />
          Delete Session
        </motion.button>
      </div>
    </div>
  )
}
