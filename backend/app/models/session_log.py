from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SessionLog(Base):
    __tablename__ = "session_log"
    __table_args__ = (
        Index("ix_session_log_visitor_started", "visitor_id", text("started_at DESC")),
        Index("ix_session_log_ip_started", "ip_hash", text("started_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    visitor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
