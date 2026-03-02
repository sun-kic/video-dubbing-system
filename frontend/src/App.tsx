import { FormEvent, useEffect, useMemo, useState } from "react";

import { createDubbingJob, getTaskStatus, uploadMedia } from "./api";
import type { JobStatus, TaskStatusResponse } from "./types";

function parseSpeakerMap(input: string): Record<string, string> {
  return input
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .reduce((acc, line) => {
      const [speaker, ...rest] = line.split("=");
      if (speaker && rest.length > 0) {
        acc[speaker.trim()] = rest.join("=").trim();
      }
      return acc;
    }, {} as Record<string, string>);
}

export default function App() {
  const [videoPath, setVideoPath] = useState("");
  const [targetLanguage, setTargetLanguage] = useState("en");
  const [speakerMapInput, setSpeakerMapInput] = useState("SPEAKER_00=/path/to/speaker0.wav");
  const [taskId, setTaskId] = useState("");
  const [status, setStatus] = useState<JobStatus | "">("");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<TaskStatusResponse["result"]>();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isTerminal = useMemo(() => status === "SUCCESS" || status === "FAILURE" || status === "REVOKED", [status]);

  useEffect(() => {
    if (!taskId || isTerminal) {
      return;
    }

    const timer = setInterval(async () => {
      try {
        const response = await getTaskStatus(taskId);
        setStatus(response.status);
        setProgress(response.progress ?? 0);
        setMessage(response.message ?? "");
        setResult(response.result);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Status fetch failed");
      }
    }, 3000);

    return () => clearInterval(timer);
  }, [taskId, isTerminal]);

  async function onUpload(file: File | null) {
    if (!file) return;
    setMessage("Uploading media...");
    try {
      const uploaded = await uploadMedia(file);
      setVideoPath(uploaded.path);
      setMessage(`Uploaded: ${uploaded.filename}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed");
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage("");
    setResult(undefined);
    setProgress(0);
    try {
      const created = await createDubbingJob({
        video_path: videoPath,
        target_language: targetLanguage,
        speaker_voice_map: parseSpeakerMap(speakerMapInput),
      });
      setTaskId(created.task_id);
      setStatus(created.status);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to create job");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="container">
      <h1>Video Dubbing System</h1>
      <p>ASR + diarization + multi-character XTTS voice cloning</p>

      <form className="card" onSubmit={onSubmit}>
        <label>
          Upload Source Video
          <input type="file" accept="video/*" onChange={(e) => onUpload(e.target.files?.[0] ?? null)} />
        </label>

        <label>
          Video Path
          <input value={videoPath} onChange={(e) => setVideoPath(e.target.value)} placeholder="/tmp/video-dubbing/storage/uploads/123.mp4" required />
        </label>

        <label>
          Target Language
          <input value={targetLanguage} onChange={(e) => setTargetLanguage(e.target.value)} placeholder="en" required />
        </label>

        <label>
          Speaker Voice Map
          <textarea
            rows={5}
            value={speakerMapInput}
            onChange={(e) => setSpeakerMapInput(e.target.value)}
            placeholder="SPEAKER_00=/absolute/path/ref0.wav\nSPEAKER_01=/absolute/path/ref1.wav"
          />
        </label>

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : "Create Dubbing Job"}
        </button>
      </form>

      <section className="card">
        <h2>Job Status</h2>
        <p>Task ID: {taskId || "-"}</p>
        <p>Status: {status || "-"}</p>
        <p>Progress: {Math.round(progress * 100)}%</p>
        <p>{message}</p>
        {result?.output_video && (
          <p>
            Output Video: <code>{result.output_video}</code>
          </p>
        )}
      </section>
    </main>
  );
}
