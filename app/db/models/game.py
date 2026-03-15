from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

if TYPE_CHECKING:
    from .user import User
    from .character import Character


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    game_users: Mapped[list["GameUser"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan"
    )


class GameUser(Base):
    __tablename__ = "game_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))  # Исправлено
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))

    game: Mapped["Game"] = relationship("Game", back_populates="game_users")
    user: Mapped["User"] = relationship("User", back_populates="game_users")
    character: Mapped["Character"] = relationship("Character", back_populates="game_users")
