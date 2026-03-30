export type JobStatus = "pending" | "uploading" | "separating" | "transcribing" | "generating" | "done" | "error"
export type Tuning = "standard" | "drop_d" | "open_g" | "half_down" | "open_e"

export const TUNING_LABELS: Record<Tuning, string> = {
  standard: "Standard (EADGBe)",
  drop_d: "Drop D (DADGBe)",
  open_g: "Open G (DGDGBd)",
  half_down: "Half Step Down (Eb Ab Db Gb Bb Eb)",
  open_e: "Open E (EBE G#Be)",
}

export interface JobStatusResponse {
  job_id: string
  status: JobStatus
  step_message: string
  progress_pct: number
  error_message?: string
}

export interface ChordEvent {
  time: number
  chord: string
  confidence: number
  roman_numeral?: string
}

export interface TabNote {
  beat: number
  string: number
  fret: number
  duration: number
  velocity: number
}

export interface TabMeasure {
  number: number
  notes: TabNote[]
}

export interface TabData {
  measures: TabMeasure[]
  string_count: number
  bpm: number
}

export interface JobResult {
  job_id: string
  status: JobStatus
  bpm: number | null
  key: string | null
  tuning: Tuning
  capo_suggestion: number | null
  chords: ChordEvent[] | null
  tab_data: TabData | null
  download_urls: {
    gp5?: string
    midi?: string
    musicxml?: string
  }
}
