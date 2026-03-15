from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey, Boolean, BigInteger
from app.db.session import Base  # async declarative base
from typing import Optional, List
from datetime import datetime


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    health: Mapped[int] = mapped_column(Integer, nullable=False)
