"""SQLAlchemy ORM models for DotaBlitz."""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Hero(Base):
    __tablename__ = "heroes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    localized_name: Mapped[str] = mapped_column(String(100))
    primary_attr: Mapped[str] = mapped_column(String(10))  # str / agi / int / all
    attack_type: Mapped[str] = mapped_column(String(10))  # Melee / Ranged
    roles: Mapped[dict] = mapped_column(JSON, default=list)
    img_url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    builds: Mapped[list["HeroBuild"]] = relationship(back_populates="hero", cascade="all,delete")

    def __repr__(self) -> str:
        return f"<Hero {self.id} {self.localized_name}>"


class HeroBuild(Base):
    __tablename__ = "hero_builds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id"), index=True)
    build_type: Mapped[str] = mapped_column(String(20))  # popular / winrate / meta / situational
    patch: Mapped[str] = mapped_column(String(20), default="")
    source: Mapped[str] = mapped_column(String(20))  # opendota / dotabuff / dotafire / aggregated
    rank_filter: Mapped[str] = mapped_column(String(20), default="all")  # immortal / divine_plus / all

    # Items by game phase (lists of item internal names)
    items_starting: Mapped[dict] = mapped_column(JSON, default=list)
    items_early: Mapped[dict] = mapped_column(JSON, default=list)
    items_core: Mapped[dict] = mapped_column(JSON, default=list)
    items_late: Mapped[dict] = mapped_column(JSON, default=list)
    items_situational: Mapped[dict] = mapped_column(JSON, default=list)
    items_neutral: Mapped[dict] = mapped_column(JSON, default=list)

    # Skill order: list of 25 ints (0=Q, 1=W, 2=E, 3=R for ult, 4/5 for talents)
    skill_order: Mapped[dict] = mapped_column(JSON, default=list)

    facet: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    winrate: Mapped[float] = mapped_column(Float, default=0.0)
    pick_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    hero: Mapped["Hero"] = relationship(back_populates="builds")

    def __repr__(self) -> str:
        return f"<HeroBuild {self.id} hero={self.hero_id} type={self.build_type}>"


class GameState(Base):
    __tablename__ = "game_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    match_id: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    hero_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hero_name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    hero_level: Mapped[int] = mapped_column(Integer, default=0)
    gold: Mapped[int] = mapped_column(Integer, default=0)
    items: Mapped[dict] = mapped_column(JSON, default=dict)
    game_time: Mapped[int] = mapped_column(Integer, default=0)
    is_alive: Mapped[bool] = mapped_column(Integer, default=True)  # SQLite has no bool
    team: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # radiant / dire
    kills: Mapped[int] = mapped_column(Integer, default=0)
    deaths: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")


class BuildHistory(Base):
    __tablename__ = "build_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hero_id: Mapped[int] = mapped_column(Integer, index=True)
    build_id: Mapped[int] = mapped_column(ForeignKey("hero_builds.id"))
    used_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    match_id: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
