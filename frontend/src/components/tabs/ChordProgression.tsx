"use client"

import type { ChordEvent } from "@/lib/types"
import clsx from "clsx"

interface ChordProgressionProps {
  readonly chords: ReadonlyArray<ChordEvent>
  readonly currentTime: number
}

function findActiveChordIndex(
  chords: ReadonlyArray<ChordEvent>,
  currentTime: number
): number {
  for (let i = chords.length - 1; i >= 0; i--) {
    if (chords[i].time <= currentTime) {
      return i
    }
  }
  return -1
}

export default function ChordProgression({ chords, currentTime }: ChordProgressionProps) {
  const activeIndex = findActiveChordIndex(chords, currentTime)

  if (chords.length === 0) {
    return null
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-400">Chord Progression</h3>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {chords.map((chord, index) => {
          const isActive = index === activeIndex

          return (
            <div
              key={`${chord.time}-${chord.chord}`}
              className={clsx(
                "flex-shrink-0 rounded-lg border px-4 py-3 text-center transition-all duration-200",
                isActive
                  ? "border-accent bg-accent/10 scale-105"
                  : "border-white/10 bg-white/5"
              )}
            >
              <div
                className={clsx(
                  "text-lg font-bold",
                  isActive ? "text-white" : "text-gray-300"
                )}
              >
                {chord.chord}
              </div>
              {chord.roman_numeral && (
                <div className="text-xs text-accent mt-0.5">
                  {chord.roman_numeral}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
