from datetime import datetime
from sqlalchemy import (
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(nullable=False)
    seed_url: Mapped[str] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    finished_at: Mapped[datetime] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        default="pending"
    )  # 'running', 'done', 'cancelled'
    max_depth: Mapped[int] = mapped_column(default=3)
    max_pages: Mapped[int] = mapped_column(default=500)

    pages: Mapped[list["Page"]] = relationship("Page", back_populates="crawl_job")

    def __repr__(self):
        return f"<CrawlJob(id={self.id}, domain='{self.domain}', seed_url='{self.seed_url}', status='{self.status}')>"


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("crawl_jobs.id"), nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    depth: Mapped[int] = mapped_column(default=0)
    crawled_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    redirected_from: Mapped[str] = mapped_column(nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    is_javascript: Mapped[bool] = mapped_column(
        default=False
    )  # crawled with Playwright?
    load_time_ms: Mapped[float] = mapped_column(nullable=True)

    job: Mapped["CrawlJob"] = relationship("CrawlJob", back_populates="pages")
    links: Mapped[list["Link"]] = relationship(
        "Link", back_populates="source_page", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_pages_job_url", "job_id", "url", unique=True),)

    def __repr__(self):
        return f"<Page(id={self.id}, url='{self.url}', status_code={self.status_code})>"


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_page_id: Mapped[int] = mapped_column(ForeignKey("pages.id"), nullable=False)
    target_url: Mapped[str] = mapped_column(nullable=False)
    anchor_text: Mapped[str] = mapped_column(nullable=True)
    is_external: Mapped[bool] = mapped_column(default=False)

    source_page: Mapped["Page"] = relationship(
        "Page", foreign_keys=[source_page_id], back_populates="links"
    )

    __table_args__ = (Index("ix_links_source_target", "source_page_id", "target_url"),)


class Queue(Base):
    __tablename__ = "queue"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crawl_job_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_jobs.id"), nullable=False
    )
    url: Mapped[str] = mapped_column(nullable=False)
    depth: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="pending")  # 'pending', done', 'failed'
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("ix_queue_job_url", "crawl_job_id", "url", unique=True),
        Index("ix_queue_status", "crawl_job_id", "status"),
    )
