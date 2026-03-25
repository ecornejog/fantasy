from app.db import Base, engine, SessionLocal
from sqlalchemy import select

Base.metadata.create_all(bind=engine)

state = {
    "tournament_id": None,
    "budget": 1000,
    "page_size": 25,
    "page": 1,
    "lineups": [],
}

table = None
page_label = None
tournament_select = None
budget_input = None
page_size_select = None

def load_tournaments():
    with SessionLocal() as session:
        tournaments = session.scalars(select(Tournament).order_by(Tournament.name)).all()
        return {t.name: t.id for t in tournaments}


def format_teams_count(players):
    counts = {}
    for p in players:
        team_name = p.team.name if p.team else "Unknown"
        counts[team_name] = counts.get(team_name, 0) + 1
    return " | ".join(f"{team} ({count})" for team, count in counts.items())


def refresh_table():
    global table, page_label

    if not state["lineups"]:
        table.rows = []
        page_label.text = "No lineups yet"
        return

    total_pages = ceil(len(state["lineups"]) / state["page_size"])
    state["page"] = max(1, min(state["page"], total_pages))

    start = (state["page"] - 1) * state["page_size"]
    end = start + state["page_size"]
    page_items = state["lineups"][start:end]

    rows = []
    for idx, lineup in enumerate(page_items, start=start + 1):
        players = lineup["players"]
        rows.append({
            "rank": idx,
            "players": ", ".join(p.name for p in players),
            "teams": format_teams_count(players),
            "total_cost": lineup["total_cost"],
            "total_rating": round(lineup["total_rating"], 2),
        })

    table.rows = rows
    page_label.text = f"Page {state['page']} / {total_pages} | {len(state['lineups'])} lineups"


def generate_lineups_action():
    tournament_id = state["tournament_id"]
    if not tournament_id:
        ui.notify("Select a tournament first", type="negative")
        return

    budget = int(budget_input.value)
    page_size = int(page_size_select.value)

    state["budget"] = budget
    state["page_size"] = page_size
    state["page"] = 1

    with SessionLocal() as session:
        players = get_players_for_tournament(session, tournament_id)

    if len(players) < 5:
        ui.notify("Not enough players in this tournament", type="negative")
        return

    state["lineups"] = generate_valid_lineups(
        players,
        budget=budget,
        team_size=5,
        max_per_team=2,
    )

    refresh_table()
    ui.notify(f"Generated {len(state['lineups'])} valid lineups", type="positive")


def prev_page():
    state["page"] -= 1
    refresh_table()


def next_page():
    state["page"] += 1
    refresh_table()
