import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    queue_id: Mapped[str] = mapped_column(String(36), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED", nullable=False)  # QUEUED, SCHEDULED, CLAIMED, RUNNING, COMPLETED, FAILED, RETRYING, DEAD_LETTER
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    queue: Mapped["Queue"] = relationship("Queue", back_populates="jobs")
    executions: Mapped[list["JobExecution"]] = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan", order_by="JobExecution.started_at.desc()")
    logs: Mapped[list["JobLog"]] = relationship("JobLog", back_populates="job", cascade="all, delete-orphan", order_by="JobLog.timestamp.asc()")
    dead_letter_entry: Mapped[Optional["DeadLetterJob"]] = relationship("DeadLetterJob", back_populates="job", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        Index("idx_jobs_queue_status", "queue_id", "status"),
        Index("idx_jobs_status_available", "status", "available_at"),
        Index("idx_jobs_queue_priority_available", "queue_id", "priority", "available_at"),
    )


class JobExecution(Base):
    __tablename__ = "job_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    worker_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("workers.id", ondelete="SET NULL"), nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING", nullable=False)  # RUNNING, COMPLETED, FAILED
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="executions")
    worker: Mapped[Optional["Worker"]] = relationship("Worker", back_populates="executions")
    logs: Mapped[list["JobLog"]] = relationship("JobLog", back_populates="execution", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_job_executions_job_id", "job_id"),
    )


class JobLog(Base):
    __tablename__ = "job_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    execution_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("job_executions.id", ondelete="CASCADE"), nullable=True)
    level: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)  # INFO, WARN, ERROR, DEBUG
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="logs")
    execution: Mapped[Optional["JobExecution"]] = relationship("JobExecution", back_populates="logs")

    __table_args__ = (
        Index("idx_job_logs_job_timestamp", "job_id", "timestamp"),
    )


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    queue_id: Mapped[str] = mapped_column(String(36), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_scheduled_jobs_next_run", "next_run_at"),
    )


class DeadLetterJob(Base):
    __tablename__ = "dead_letter_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    final_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="dead_letter_entry")
