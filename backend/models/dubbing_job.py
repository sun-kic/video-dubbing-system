from sqlalchemy import String, Float, ForeignKey, DateTime, JSON, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from backend.core.database import Base
from .enums import JobStatus


class DubbingJob(Base):
    """Top-level dubbing job for a video."""
    __tablename__ = "dubbing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    tts_engine: Mapped[str] = mapped_column(String(50), default="xtts")
    status: Mapped[str] = mapped_column(String(50), default=JobStatus.PENDING)
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 1.0
    current_step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_video_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="dubbing_jobs")  # noqa: F821
    segments: Mapped[list["DubbingSegment"]] = relationship(
        "DubbingSegment", back_populates="job", cascade="all, delete-orphan",
        order_by="DubbingSegment.segment_index"
    )


class DubbingSegment(Base):
    """Per-segment result within a dubbing job."""
    __tablename__ = "dubbing_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dubbing_jobs.id"), nullable=False)
    video_segment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("video_segments.id"), nullable=False)
    speaker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("speakers.id"), nullable=True)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    dubbed_audio_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tts_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_factor: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(50), default=JobStatus.PENDING)

    # Relationships
    job: Mapped["DubbingJob"] = relationship("DubbingJob", back_populates="segments")
