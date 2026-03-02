from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, JSON, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from backend.core.database import Base
from .enums import JobStatus


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    processed_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    dubbed_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # bytes
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    process_status: Mapped[str] = mapped_column(String(50), default=JobStatus.PENDING)
    extracted_audio_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="videos")  # noqa: F821
    segments: Mapped[list["VideoSegment"]] = relationship(
        "VideoSegment", back_populates="video", cascade="all, delete-orphan",
        order_by="VideoSegment.start_time"
    )


class VideoSegment(Base):
    """A time-stamped speech segment extracted from the video."""
    __tablename__ = "video_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id"), nullable=False)
    speaker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("speakers.id"), nullable=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    dubbed_audio_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    segment_index: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="segments")
    speaker: Mapped["Speaker | None"] = relationship("Speaker", back_populates="segments")  # noqa: F821

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
