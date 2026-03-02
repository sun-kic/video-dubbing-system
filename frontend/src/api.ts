import type { CreateJobRequest, CreateJobResponse, TaskStatusResponse } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function uploadMedia(file: File): Promise<{ path: string; filename: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/media/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json();
}

export async function createDubbingJob(payload: CreateJobRequest): Promise<CreateJobResponse> {
  const response = await fetch(`${BASE_URL}/dubbing/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const response = await fetch(`${BASE_URL}/dubbing/jobs/${taskId}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
