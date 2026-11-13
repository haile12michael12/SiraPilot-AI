"""Account-scoped PostgreSQL repositories."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.postgres.models import Job


class JobRepository:
    def __init__(self, session: Session, account_id: UUID) -> None:
        self._session = session
        self._account_id = account_id

    def get(self, job_id: UUID) -> Job | None:
        return self._session.scalar(
            select(Job).where(Job.account_id == self._account_id, Job.id == job_id)
        )

    def list_recent(self, *, limit: int = 50) -> list[Job]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        statement = (
            select(Job)
            .where(Job.account_id == self._account_id)
            .order_by(Job.updated_at.desc(), Job.id)
            .limit(limit)
        )
        return list(self._session.scalars(statement))

    def create(
        self,
        *,
        title: str | None,
        company: str | None,
        status: str = "new",
    ) -> Job:
        job = Job(
            id=uuid4(),
            account_id=self._account_id,
            title=title,
            company=company,
            status=status,
        )
        self._session.add(job)
        return job
