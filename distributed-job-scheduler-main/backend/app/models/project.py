import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RetryPolicy(Base):
    __tablename__ = "retry_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy: Mapped[str] = mapped_column(String(50), default="exponential", nullable=False)  # fixed, linear, exponential
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    initial_delay_seconds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    backoff_multiplier: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)

    queues: Mapped[list["Queue"]] = relationship("Queue", back_populates="retry_policy")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="projects")
    queues: Mapped[list["Queue"]] = relationship("Queue", back_populates="project", cascade="all, delete-orphan")


class Queue(Base):
    __tablename__ = "queues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    concurrency_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_policy_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("retry_policies.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="queues")
    retry_policy: Mapped[Optional["RetryPolicy"]] = relationship("RetryPolicy", back_populates="queues")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="queue", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_queues_project_name", "project_id", "name", unique=True),
    )
