import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from app.database import engine, AsyncSessionLocal, Base
from app.models import (
    User,
    Organization,
    OrganizationMember,
    Project,
    Queue,
    RetryPolicy,
    Job,
    JobLog,
    ScheduledJob,
)
from app.utils.security import hash_password


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def seed():
    print("[SEED] Starting database seeding...")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import select
        existing_user = await db.execute(select(User).where(User.email == "admin@example.com"))
        if existing_user.scalar_one_or_none():
            print("[INFO] Database already seeded. Skipping.")
            return

        now = utcnow()

        # 1. Admin User
        admin_user = User(
            id=str(uuid.uuid4()),
            email="admin@example.com",
            password_hash=hash_password("password123"),
            name="Admin User",
            created_at=now,
        )
        db.add(admin_user)
        await db.flush()
        print(f"[OK] Created admin user: {admin_user.email} (password: password123)")

        # 2. Organization
        org = Organization(
            id=str(uuid.uuid4()),
            name="Acme Corp Distributed Systems",
            created_at=now,
        )
        db.add(org)
        await db.flush()

        member = OrganizationMember(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            user_id=admin_user.id,
            role="owner",
            created_at=now,
        )
        db.add(member)

        # 3. Retry Policies
        policy_exp = RetryPolicy(
            id=str(uuid.uuid4()),
            name="Exponential Backoff (Default)",
            strategy="exponential",
            max_attempts=3,
            initial_delay_seconds=5,
            backoff_multiplier=2.0,
        )
        policy_linear = RetryPolicy(
            id=str(uuid.uuid4()),
            name="Linear Backoff",
            strategy="linear",
            max_attempts=4,
            initial_delay_seconds=5,
            backoff_multiplier=1.0,
        )
        policy_fixed = RetryPolicy(
            id=str(uuid.uuid4()),
            name="Fixed Quick Retry",
            strategy="fixed",
            max_attempts=3,
            initial_delay_seconds=3,
            backoff_multiplier=1.0,
        )
        db.add_all([policy_exp, policy_linear, policy_fixed])
        await db.flush()
        print("[OK] Created retry policies (Exponential, Linear, Fixed)")

        # 4. Project
        project = Project(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            name="Core Background Jobs",
            description="Production asynchronous workload processing pipelines and scheduled workers.",
            created_at=now,
        )
        db.add(project)
        await db.flush()
        print(f"[OK] Created project: {project.name}")

        # 5. Queues
        queue_default = Queue(
            id=str(uuid.uuid4()),
            project_id=project.id,
            name="default",
            priority=0,
            concurrency_limit=5,
            paused=False,
            retry_policy_id=policy_exp.id,
            created_at=now,
            updated_at=now,
        )
        queue_high = Queue(
            id=str(uuid.uuid4()),
            project_id=project.id,
            name="high-priority",
            priority=10,
            concurrency_limit=10,
            paused=False,
            retry_policy_id=policy_fixed.id,
            created_at=now,
            updated_at=now,
        )
        queue_email = Queue(
            id=str(uuid.uuid4()),
            project_id=project.id,
            name="email",
            priority=5,
            concurrency_limit=3,
            paused=False,
            retry_policy_id=policy_linear.id,
            created_at=now,
            updated_at=now,
        )
        queue_scheduled = Queue(
            id=str(uuid.uuid4()),
            project_id=project.id,
            name="scheduled",
            priority=2,
            concurrency_limit=2,
            paused=False,
            retry_policy_id=policy_exp.id,
            created_at=now,
            updated_at=now,
        )
        db.add_all([queue_default, queue_high, queue_email, queue_scheduled])
        await db.flush()
        print("[OK] Created queues (default, high-priority, email, scheduled)")

        # 6. Sample Jobs
        sample_jobs_data = [
            (
                queue_default.id,
                "echo",
                {"message": "Hello from Distributed Job Scheduler!", "timestamp": now.isoformat()},
                0,
                "QUEUED",
                now,
            ),
            (
                queue_default.id,
                "sleep",
                {"seconds": 2, "task_name": "background-data-sync"},
                0,
                "QUEUED",
                now,
            ),
            (
                queue_high.id,
                "calculation",
                {"operation": "fibonacci", "n": 35},
                10,
                "QUEUED",
                now,
            ),
            (
                queue_email.id,
                "email_simulation",
                {"to": "user@example.com", "subject": "Welcome to our Platform", "template": "onboarding_v1"},
                5,
                "QUEUED",
                now,
            ),
            (
                queue_default.id,
                "intentional_failure",
                {"error": "Simulated external payment gateway timeout", "fail_times": 5},
                0,
                "QUEUED",
                now,
            ),
            (
                queue_scheduled.id,
                "echo",
                {"message": "Delayed job scheduled 30 seconds into the future"},
                2,
                "SCHEDULED",
                now + timedelta(seconds=30),
            ),
        ]

        for q_id, j_type, payload, priority, status_val, avail_at in sample_jobs_data:
            j_id = str(uuid.uuid4())
            job = Job(
                id=j_id,
                queue_id=q_id,
                job_type=j_type,
                payload=payload,
                status=status_val,
                priority=priority,
                available_at=avail_at,
                attempts=0,
                max_attempts=3,
                created_at=now,
                updated_at=now,
            )
            db.add(job)
            log = JobLog(
                id=str(uuid.uuid4()),
                job_id=j_id,
                level="INFO",
                message=f"Seeded job of type '{j_type}' with status='{status_val}'",
                timestamp=now,
            )
            db.add(log)

        # 7. Scheduled Recurring Job
        sched_job = ScheduledJob(
            id=str(uuid.uuid4()),
            queue_id=queue_scheduled.id,
            job_type="echo",
            payload={"message": "Periodic health check ping", "source": "cron_scheduler"},
            cron_expression="*/5 * * * *",
            next_run_at=now + timedelta(minutes=5),
            enabled=True,
            created_at=now,
        )
        db.add(sched_job)

        await db.commit()
        print("[OK] Successfully seeded demo data!")


if __name__ == "__main__":
    asyncio.run(seed())
