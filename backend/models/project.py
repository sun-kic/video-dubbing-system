from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from backend.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_language: Mapped[str] = mapped_column(String(10), default="zh")
    target_language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    videos: Mapped[list["Video"]] = relationship(  # noqa: F821
        "Video", back_populates="project", cascade="all, delete-orphan"
    )
    speakers: Mapped[list["Speaker"]] = relationship(  # noqa: F821
        "Speaker", back_populates="project", cascade="all, delete-orphan"
    )
    dubbing_jobs: Mapped[list["DubbingJob"]] = relationship(  # noqa: F821
        "DubbingJob", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"
