from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey, Boolean, BigInteger
from .session import Base  # async declarative base
from typing import Optional, List
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))

    auth_tokens: Mapped[List["AuthToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="auth_tokens")
