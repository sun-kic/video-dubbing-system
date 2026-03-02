export type JobStatus = "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY" | "REVOKED";

export interface CreateJobRequest {
  video_path: string;
  target_language: string;
  speaker_voice_map: Record<string, string>;
}

export interface CreateJobResponse {
  task_id: string;
  status: JobStatus;
  submitted_at: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: JobStatus;
  progress: number;
  message: string;
  result?: {
    input_video: string;
    output_video: string;
    transcript_segments: number;
    speakers_detected: string[];
    generated_audio_dir: string;
    created_at: string;
  };
}
