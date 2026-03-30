"use client"

import { useCallback, useEffect, useRef, useState } from "react"

interface TabPlayerProps {
  readonly gp5Url: string
  readonly downloadUrls: {
    readonly gp5?: string
    readonly midi?: string
    readonly musicxml?: string
  }
}

export default function TabPlayer({ gp5Url, downloadUrls }: TabPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const playerRef = useRef<unknown>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [tempo, setTempo] = useState(100)
  const [currentMeasure, setCurrentMeasure] = useState(1)
  const [isLoaded, setIsLoaded] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    if (!containerRef.current || !gp5Url) return

    let api: Record<string, unknown> | null = null
    let cancelled = false

    const initAlphaTab = async () => {
      try {
        const alphaTabModule = await import("@coderline/alphatab")

        if (cancelled || !containerRef.current) return

        const settings = new alphaTabModule.Settings()
        settings.core.fontDirectory = "https://cdn.jsdelivr.net/npm/@coderline/alphatab@latest/dist/font/"
        settings.core.file = gp5Url
        settings.core.enableLazyLoading = true
        settings.player.enablePlayer = true
        settings.player.enableUserInteraction = true
        settings.player.soundFont = "https://cdn.jsdelivr.net/npm/@coderline/alphatab@latest/dist/soundfont/sonivox.sf2"
        settings.display.staveProfile = alphaTabModule.StaveProfile.TabMixed
        settings.display.scale = 0.9

        api = new (alphaTabModule.AlphaTabApi as unknown as new (el: HTMLElement, settings: unknown) => Record<string, unknown>)(
          containerRef.current,
          settings
        )

        playerRef.current = api

        if (typeof api.scoreLoaded === "object" && api.scoreLoaded !== null && "on" in (api.scoreLoaded as Record<string, unknown>)) {
          (api.scoreLoaded as { on: (cb: () => void) => void }).on(() => {
            if (!cancelled) setIsLoaded(true)
          })
        }

        if (typeof api.playerStateChanged === "object" && api.playerStateChanged !== null && "on" in (api.playerStateChanged as Record<string, unknown>)) {
          (api.playerStateChanged as { on: (cb: (e: { state: number }) => void) => void }).on((e) => {
            if (!cancelled) setIsPlaying(e.state === 1)
          })
        }

        if (typeof api.playedBeatChanged === "object" && api.playedBeatChanged !== null && "on" in (api.playedBeatChanged as Record<string, unknown>)) {
          (api.playedBeatChanged as { on: (cb: (beat: { voice?: { bar?: { index?: number } } }) => void) => void }).on((beat) => {
            const barIndex = beat?.voice?.bar?.index
            if (!cancelled && typeof barIndex === "number") {
              setCurrentMeasure(barIndex + 1)
            }
          })
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Failed to load alphaTab")
        }
      }
    }

    initAlphaTab()

    return () => {
      cancelled = true
      if (api && typeof api.destroy === "function") {
        (api.destroy as () => void)()
      }
      playerRef.current = null
    }
  }, [gp5Url])

  const handlePlayPause = useCallback(() => {
    const api = playerRef.current as Record<string, unknown> | null
    if (api && typeof api.playPause === "function") {
      (api.playPause as () => void)()
    }
  }, [])

  const handleTempoChange = useCallback((newTempo: number) => {
    setTempo(newTempo)
    const api = playerRef.current as Record<string, unknown> | null
    if (api && typeof api.playbackSpeed === "number") {
      (api as Record<string, unknown>).playbackSpeed = newTempo / 100
    }
  }, [])

  if (loadError) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-center text-red-400">
        <p className="font-medium">Failed to load tab player</p>
        <p className="text-sm mt-1">{loadError}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Controls bar */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl bg-white/5 border border-white/10 p-4">
        {/* Play/Pause */}
        <button
          onClick={handlePlayPause}
          disabled={!isLoaded}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-white transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {isPlaying ? (
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
            </svg>
          ) : (
            <svg className="h-5 w-5 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* Measure indicator */}
        <div className="text-sm text-gray-400">
          Measure <span className="text-white font-medium">{currentMeasure}</span>
        </div>

        {/* Speed slider */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-gray-500">Speed</span>
          <input
            type="range"
            min={25}
            max={150}
            value={tempo}
            onChange={(e) => handleTempoChange(Number(e.target.value))}
            className="w-24 accent-accent"
          />
          <span className="text-sm text-gray-400 w-10 text-right">{tempo}%</span>
        </div>

        {/* Download buttons */}
        <div className="flex items-center gap-2">
          {downloadUrls.gp5 && (
            <a
              href={downloadUrls.gp5}
              download
              className="rounded-lg border border-white/20 px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-white/10"
            >
              GP5
            </a>
          )}
          {downloadUrls.midi && (
            <a
              href={downloadUrls.midi}
              download
              className="rounded-lg border border-white/20 px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-white/10"
            >
              MIDI
            </a>
          )}
          {downloadUrls.musicxml && (
            <a
              href={downloadUrls.musicxml}
              download
              className="rounded-lg border border-white/20 px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-white/10"
            >
              MusicXML
            </a>
          )}
        </div>
      </div>

      {/* AlphaTab container */}
      <div
        ref={containerRef}
        className="min-h-[400px] rounded-xl bg-white/[0.03] border border-white/10 overflow-auto"
      >
        {!isLoaded && !loadError && (
          <div className="flex h-[400px] items-center justify-center text-gray-500">
            <div className="text-center space-y-2">
              <div className="h-8 w-8 mx-auto animate-spin rounded-full border-2 border-accent border-t-transparent" />
              <p className="text-sm">Loading tablature...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
