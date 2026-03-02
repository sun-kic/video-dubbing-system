from sqlalchemy import String, Float, ForeignKey, DateTime, JSON, Boolean, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from backend.core.database import Base


class Speaker(Base):
    """A detected or manually defined speaker in a project."""
    __tablename__ = "speakers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "SPEAKER_00"
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Hex color for UI
    voice_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("voice_profiles.id"), nullable=True
    )
    total_speech_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="speakers")  # noqa: F821
    voice_profile: Mapped["VoiceProfile | None"] = relationship(
        "VoiceProfile", back_populates="speakers", foreign_keys=[voice_profile_id]
    )
    segments: Mapped[list["VideoSegment"]] = relationship(  # noqa: F821
        "VideoSegment", back_populates="speaker"
    )

    def __repr__(self) -> str:
        return f"<Speaker label={self.label!r} name={self.display_name!r}>"


class VoiceProfile(Base):
    """A cloned or reference voice that can be assigned to speakers."""
    __tablename__ = "voice_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_audio_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    embedding_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    embedding_vector: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tts_engine: Mapped[str] = mapped_column(String(50), default="xtts")
    is_cloned: Mapped[bool] = mapped_column(Boolean, default=False)
    clone_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    speakers: Mapped[list["Speaker"]] = relationship(
        "Speaker", back_populates="voice_profile", foreign_keys="Speaker.voice_profile_id"
    )
