"use client"

import { TUNING_LABELS } from "@/lib/types"
import type { Tuning } from "@/lib/types"

interface Props {
  readonly bpm: number | null
  readonly keyName: string | null
  readonly tuning: Tuning
  readonly capoSuggestion: number | null
}

export default function MetadataBar({ bpm, keyName, tuning, capoSuggestion }: Props) {
  const tuningLabel = TUNING_LABELS[tuning]

  return (
    <div className="flex flex-wrap items-center gap-3">
      {keyName && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm text-gray-300">
          <span className="text-gray-500 text-xs">Key</span>
          <span className="font-medium text-white">{keyName}</span>
        </span>
      )}
      {bpm !== null && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm text-gray-300">
          <span className="text-gray-500 text-xs">BPM</span>
          <span className="font-medium text-white">{Math.round(bpm)}</span>
        </span>
      )}
      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm text-gray-300">
        <span className="text-gray-500 text-xs">Tuning</span>
        <span className="font-medium text-white">{tuningLabel}</span>
      </span>
      {capoSuggestion !== null && capoSuggestion > 0 && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/30 text-sm text-blue-300">
          <span className="text-blue-400 text-xs">Capo</span>
          <span className="font-medium text-blue-200">Fret {capoSuggestion}</span>
        </span>
      )}
    </div>
  )
}
