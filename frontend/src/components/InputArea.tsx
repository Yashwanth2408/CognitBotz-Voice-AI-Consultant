"use client"

import { useState, useRef } from "react"
import { useConversationStore } from "@/store/conversationStore"
import { Send, Mic, Square } from "lucide-react"

export default function InputArea() {
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

  const formatRecordingTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }

  return (
    <div className="border-t border-dark-border bg-dark-bg p-4">
      <div className="max-w-4xl mx-auto w-full">
        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-3 rounded-lg border border-dark-border bg-dark-surface p-2"
        >
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isLoading}
            className={`h-11 w-11 rounded-md flex items-center justify-center border transition-colors ${
              isRecording
                ? "bg-red-950/30 border-accent-danger text-red-200"
                : "bg-dark-bg border-dark-border text-dark-muted hover:text-dark-text hover:bg-dark-panel"
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title={isRecording ? "Stop recording" : "Start recording"}
          >
            {isRecording ? <Square size={18} /> : <Mic size={19} />}
          </button>

          <div className="flex-1">
            <input
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={isRecording ? `Recording ${formatRecordingTime(recordingTime)}` : "Ask about CognitBotz..."}
              disabled={isLoading || isRecording}
              className="w-full px-3 py-3 bg-transparent text-dark-text placeholder-dark-muted focus:outline-none disabled:opacity-50"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !text.trim() || isRecording}
            className="h-11 px-4 rounded-md bg-dark-text text-dark-bg font-medium flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-white/90 transition-colors"
          >
            {isLoading ? (
              <div className="w-4 h-4 rounded-full border-2 border-dark-bg border-t-transparent animate-spin" />
            ) : (
              <>
                <Send size={17} />
                <span>Send</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
