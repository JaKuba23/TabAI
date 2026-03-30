import type { Tuning, JobStatusResponse, JobResult } from "./types"

interface UploadResponse {
  job_id: string
  status: string
  message: string
}

export async function uploadAudio(file: File, tuning: Tuning): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("tuning", tuning)

  const response = await fetch("/api/jobs/upload", {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    const errorBody = await response.text()
    throw new Error(`Upload failed (${response.status}): ${errorBody}`)
  }

  return response.json() as Promise<UploadResponse>
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`/api/jobs/${jobId}/status`)

  if (!response.ok) {
    throw new Error(`Failed to get job status (${response.status})`)
  }

  return response.json() as Promise<JobStatusResponse>
}

export async function getJobResult(jobId: string): Promise<JobResult> {
  const response = await fetch(`/api/jobs/${jobId}/result`)

  if (!response.ok) {
    throw new Error(`Failed to get job result (${response.status})`)
  }

  return response.json() as Promise<JobResult>
}

export async function deleteJob(jobId: string): Promise<void> {
  const response = await fetch(`/api/jobs/${jobId}`, {
    method: "DELETE",
  })

  if (!response.ok) {
    throw new Error(`Failed to delete job (${response.status})`)
  }
}

export function createJobStatusSocket(
  jobId: string,
  onUpdate: (status: JobStatusResponse) => void,
  onError: (event: Event) => void
): () => void {
  const protocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:"
  const backendHost = process.env.NEXT_PUBLIC_WS_HOST ?? "localhost:8000"
  const ws = new WebSocket(`${protocol}//${backendHost}/ws/jobs/${jobId}`)

  ws.onmessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data as string) as JobStatusResponse
      onUpdate(data)

      if (data.status === "done" || data.status === "error") {
        ws.close()
      }
    } catch {
      // Ignore malformed messages
    }
  }

  ws.onerror = onError

  return () => {
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close()
    }
  }
}

export async function pollJobStatus(
  jobId: string,
  onUpdate: (status: JobStatusResponse) => void,
  intervalMs: number = 2000
): Promise<void> {
  const poll = async (): Promise<void> => {
    const status = await getJobStatus(jobId)
    onUpdate(status)

    if (status.status !== "done" && status.status !== "error") {
      await new Promise<void>((resolve) => setTimeout(resolve, intervalMs))
      return poll()
    }
  }

  return poll()
}
