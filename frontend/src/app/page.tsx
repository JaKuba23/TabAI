"use client"

import { useCallback, useRef, useState } from "react"
import dynamic from "next/dynamic"
import type { Tuning, JobStatus, JobStatusResponse, JobResult } from "@/lib/types"
import { TUNING_LABELS } from "@/lib/types"
import { uploadAudio, getJobResult, createJobStatusSocket, pollJobStatus } from "@/lib/api"
import DropZone from "@/components/upload/DropZone"
import TuningSelector from "@/components/upload/TuningSelector"
import ProgressSteps from "@/components/upload/ProgressSteps"
import MetadataBar from "@/components/tabs/MetadataBar"
import ChordProgression from "@/components/tabs/ChordProgression"

const TabPlayer = dynamic(() => import("@/components/player/TabPlayer"), { ssr: false })

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null)
  const [tuning, setTuning] = useState<Tuning>("standard")
  const [isProcessing, setIsProcessing] = useState(false)
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null)
  const [result, setResult] = useState<JobResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const wsCleanupRef = useRef<(() => void) | null>(null)

  const reset = useCallback(() => {
    wsCleanupRef.current?.()
    wsCleanupRef.current = null
    setFile(null)
    setTuning("standard")
    setIsProcessing(false)
    setJobStatus(null)
    setResult(null)
    setError(null)
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!file) return

    setIsProcessing(true)
    setError(null)
    setJobStatus({
      job_id: "",
      status: "uploading",
      step_message: "Uploading audio file...",
      progress_pct: 0,
    })

    try {
      const uploadResponse = await uploadAudio(file, tuning)
      const jobId = uploadResponse.job_id

      const handleUpdate = async (status: JobStatusResponse) => {
        setJobStatus(status)

        if (status.status === "done") {
          const jobResult = await getJobResult(jobId)
          setResult(jobResult)
          setIsProcessing(false)
        }

        if (status.status === "error") {
          setError(status.error_message ?? "An unknown error occurred")
          setIsProcessing(false)
        }
      }

      // Try WebSocket first, fall back to polling
      try {
        const cleanup = createJobStatusSocket(
          jobId,
          handleUpdate,
          () => {
            // WebSocket error, fall back to polling
            pollJobStatus(jobId, handleUpdate).catch((pollErr) => {
              setError(pollErr instanceof Error ? pollErr.message : "Polling failed")
              setIsProcessing(false)
            })
          }
        )

        wsCleanupRef.current = cleanup
      } catch {
        // WebSocket not available, use polling
        await pollJobStatus(jobId, handleUpdate)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
      setIsProcessing(false)
    }
  }, [file, tuning])

  const showUploadForm = !isProcessing && !result
  const showProgress = isProcessing && jobStatus
  const showResult = !isProcessing && result

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-white/10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-tight">
              <span className="text-accent">Tab</span>AI
            </h1>
            <span className="rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-accent">
              Beta
            </span>
          </div>
          <div className="flex items-center gap-4">
            <a href="#pricing" className="text-sm text-gray-400 hover:text-white transition-colors">
              Pricing
            </a>
            <button className="rounded-lg border border-white/20 px-4 py-1.5 text-sm font-medium text-gray-300 transition-colors hover:bg-white/10">
              Sign In
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12">
        {/* Hero (shown when idle) */}
        {showUploadForm && !file && (
          <div className="mb-10 text-center">
            <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Turn any song into
              <br />
              <span className="text-accent">guitar tabs</span>
            </h2>
            <p className="mt-4 text-lg text-gray-400">
              Upload a song and get playable tablature in seconds, powered by AI.
            </p>
          </div>
        )}

        {/* Upload form */}
        {showUploadForm && (
          <div className="space-y-6">
            <DropZone onFileSelect={setFile} file={file} />

            {file && (
              <>
                <TuningSelector value={tuning} onChange={setTuning} />

                <button
                  onClick={handleSubmit}
                  className="w-full rounded-xl bg-accent py-3 text-lg font-semibold text-white transition-opacity hover:opacity-90"
                >
                  Generate Tabs
                </button>
              </>
            )}
          </div>
        )}

        {/* Processing progress */}
        {showProgress && jobStatus && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-center">Processing your track</h2>
            <ProgressSteps
              status={jobStatus.status}
              stepMessage={jobStatus.step_message}
              progressPct={jobStatus.progress_pct}
            />
          </div>
        )}

        {/* Error state */}
        {error && !isProcessing && (
          <div className="space-y-4 text-center">
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6">
              <p className="text-red-400 font-medium">Something went wrong</p>
              <p className="text-sm text-red-400/70 mt-1">{error}</p>
            </div>
            <button
              onClick={reset}
              className="rounded-xl border border-white/20 px-6 py-2.5 text-sm font-medium text-gray-300 transition-colors hover:bg-white/10"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Result */}
        {showResult && result && (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">Your Tabs</h2>
              <button
                onClick={reset}
                className="rounded-lg border border-white/20 px-4 py-1.5 text-sm font-medium text-gray-300 transition-colors hover:bg-white/10"
              >
                New Upload
              </button>
            </div>

            <MetadataBar
              bpm={result.bpm}
              keyName={result.key}
              tuning={TUNING_LABELS[result.tuning]}
              capoSuggestion={result.capo_suggestion}
            />

            {result.download_urls.gp5 && (
              <TabPlayer
                gp5Url={result.download_urls.gp5}
                downloadUrls={result.download_urls}
              />
            )}

            {result.chords && result.chords.length > 0 && (
              <ChordProgression chords={result.chords} currentTime={0} />
            )}
          </div>
        )}
      </main>
    </div>
  )
}
