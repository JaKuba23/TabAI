"use client"

import { useCallback, useRef, useState } from "react"

const ACCEPTED_TYPES = [
  "audio/mpeg",
  "audio/wav",
  "audio/flac",
  "audio/x-flac",
  "audio/mp4",
  "audio/m4a",
  "audio/x-m4a",
  "audio/ogg",
  "audio/aac",
]

const ACCEPTED_EXTENSIONS = ".mp3,.wav,.flac,.m4a,.ogg,.aac"

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface DropZoneProps {
  readonly onFileSelect: (file: File) => void
  readonly file: File | null
}

export default function DropZone({ onFileSelect, file }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragOver(false)

      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile && ACCEPTED_TYPES.includes(droppedFile.type)) {
        onFileSelect(droppedFile)
      }
    },
    [onFileSelect]
  )

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0]
      if (selectedFile) {
        onFileSelect(selectedFile)
      }
    },
    [onFileSelect]
  )

  const handleClick = useCallback(() => {
    inputRef.current?.click()
  }, [])

  const borderColor = isDragOver
    ? "border-accent bg-accent/10"
    : file
      ? "border-green-500/50 bg-green-500/5"
      : "border-white/20 hover:border-white/40"

  return (
    <div
      onClick={handleClick}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={`relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200 ${borderColor}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        onChange={handleInputChange}
        className="hidden"
      />

      {file ? (
        <div className="space-y-1">
          <div className="text-lg font-medium text-green-400">{file.name}</div>
          <div className="text-sm text-gray-400">{formatFileSize(file.size)}</div>
          <div className="text-xs text-gray-500 mt-2">Click or drop to replace</div>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="text-4xl">
            <svg className="w-12 h-12 mx-auto text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
          <div className="text-gray-300 font-medium">Drop an audio file here</div>
          <div className="text-sm text-gray-500">or click to browse</div>
          <div className="text-xs text-gray-600">MP3, WAV, FLAC, M4A, OGG, AAC</div>
        </div>
      )}
    </div>
  )
}
