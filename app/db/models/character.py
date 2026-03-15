from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey, Boolean, BigInteger
from app.db.session import Base  # async declarative base
from typing import Optional, List
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game import GameUser


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    health: Mapped[int] = mapped_column(Integer, nullable=False)

    game_users: Mapped[list["GameUser"]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan"
    )
