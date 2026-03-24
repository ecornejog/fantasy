from collections import Counter
from itertools import combinations
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Player, Team, TournamentTeam


def get_players_for_tournament(session: Session, tournament_id: int):
    stmt = (
        select(Player)
        .join(Team, Player.team_id == Team.id)
        .join(TournamentTeam, TournamentTeam.team_id == Team.id)
        .where(TournamentTeam.tournament_id == tournament_id)
    )
    return list(session.scalars(stmt).all())


def generate_valid_lineups(players, budget=1000, team_size=5, max_per_team=2):
    lineups = []

    for combo in combinations(players, team_size):
        total_cost = sum(p.price for p in combo)
        if total_cost > budget:
            continue

        counts = Counter(p.team_id for p in combo)
        if any(count > max_per_team for count in counts.values()):
            continue

        total_rating = sum(p.rating for p in combo)

        lineups.append({
            "players": combo,
            "total_cost": total_cost,
            "total_rating": total_rating,
        })

    lineups.sort(key=lambda x: (x["total_rating"], -x["total_cost"]), reverse=True)
    return lineups