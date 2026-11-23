import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ONLINE", nullable=False)  # ONLINE, OFFLINE, STOPPING
    concurrency: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    heartbeats: Mapped[list["WorkerHeartbeat"]] = relationship("WorkerHeartbeat", back_populates="worker", cascade="all, delete-orphan", order_by="WorkerHeartbeat.heartbeat_at.desc()")
    executions: Mapped[list["JobExecution"]] = relationship("JobExecution", back_populates="worker")


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_id: Mapped[str] = mapped_column(String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    active_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_slots: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    worker: Mapped["Worker"] = relationship("Worker", back_populates="heartbeats")

    __table_args__ = (
        Index("idx_worker_heartbeats_worker_time", "worker_id", "heartbeat_at"),
    )
