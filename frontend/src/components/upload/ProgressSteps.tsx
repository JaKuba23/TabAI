"use client"

import type { JobStatus } from "@/lib/types"

interface ProgressStepsProps {
  readonly status: JobStatus
  readonly stepMessage: string
  readonly progressPct: number
}

interface Step {
  readonly key: JobStatus
  readonly label: string
}

const STEPS: ReadonlyArray<Step> = [
  { key: "uploading", label: "Uploading" },
  { key: "separating", label: "Isolating guitar" },
  { key: "transcribing", label: "Transcribing" },
  { key: "generating", label: "Generating tab" },
  { key: "done", label: "Done" },
]

function getStepState(
  stepKey: JobStatus,
  currentStatus: JobStatus
): "done" | "active" | "pending" {
  const stepIndex = STEPS.findIndex((s) => s.key === stepKey)
  const currentIndex = STEPS.findIndex((s) => s.key === currentStatus)

  if (currentStatus === "done") return "done"
  if (currentStatus === "error") {
    return stepIndex < currentIndex ? "done" : stepIndex === currentIndex ? "active" : "pending"
  }
  if (stepIndex < currentIndex) return "done"
  if (stepIndex === currentIndex) return "active"
  return "pending"
}

export default function ProgressSteps({ status, stepMessage, progressPct }: ProgressStepsProps) {
  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">{stepMessage}</span>
          <span className="text-gray-500">{Math.round(progressPct)}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Step list */}
      <div className="space-y-3">
        {STEPS.map((step) => {
          const state = getStepState(step.key, status)

          return (
            <div key={step.key} className="flex items-center gap-3">
              {/* Indicator */}
              {state === "done" ? (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-green-500/20">
                  <svg className="h-4 w-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              ) : state === "active" ? (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/20">
                  <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-accent" />
                </div>
              ) : (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white/5">
                  <div className="h-2 w-2 rounded-full bg-gray-600" />
                </div>
              )}

              {/* Label */}
              <span
                className={
                  state === "done"
                    ? "text-green-400"
                    : state === "active"
                      ? "text-accent font-medium"
                      : "text-gray-600"
                }
              >
                {step.label}
              </span>
            </div>
          )
        })}
      </div>

      {/* Error state */}
      {status === "error" && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          An error occurred during processing. Please try again.
        </div>
      )}
    </div>
  )
}
