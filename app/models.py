from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, DateTime
)
from sqlalchemy.orm import relationship
from app.db import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    hltv_ranking = Column(Integer, nullable=True)
    hltv_points = Column(Integer, nullable=True)
    valve_rank = Column(Integer, nullable=True)
    valve_points = Column(Integer, nullable=True)

    players = relationship("Player", back_populates="team")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    rating = Column(Float, nullable=False)
    price = Column(Integer, nullable=False)

    team = relationship("Team", back_populates="players")


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    format_type = Column(String, nullable=False)
    num_teams = Column(Integer, nullable=False)
    has_bo5_final = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tournament_teams = relationship("TournamentTeam", back_populates="tournament")


class TournamentTeam(Base):
    __tablename__ = "tournament_teams"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    tournament = relationship("Tournament", back_populates="tournament_teams")
    team = relationship("Team")


class Lineup(Base):
    __tablename__ = "lineups"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False, index=True)
    total_cost = Column(Integer, nullable=False)
    total_rating = Column(Float, nullable=False)


class LineupPlayer(Base):
    __tablename__ = "lineup_players"

    id = Column(Integer, primary_key=True, index=True)
    lineup_id = Column(Integer, ForeignKey("lineups.id"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)


class RoleStat(Base):
    __tablename__ = "role_stats"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    prob_big = Column(Float, nullable=False, default=0)
    prob_small = Column(Float, nullable=False, default=0)


class Booster(Base):
    __tablename__ = "boosters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)


class BoosterStat(Base):
    __tablename__ = "booster_stats"

    id = Column(Integer, primary_key=True, index=True)
    booster_id = Column(Integer, ForeignKey("boosters.id"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    success_rate = Column(Float, nullable=False, default=0)