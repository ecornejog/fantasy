from math import ceil
from sqlalchemy import select
from nicegui import ui

from app.db import Base, engine, SessionLocal
from app.models import Tournament
from app.services.lineups import get_players_for_tournament, generate_valid_lineups

from app.models import Team, Player, Tournament
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


@ui.page("/")
def home():
    global table, page_label, tournament_select, budget_input, page_size_select

    ui.label("Fantasy Optimizer - Phase 1").classes("text-2xl font-bold mb-4")

    tournaments = load_tournaments()
    if not tournaments:
        ui.label("No tournaments found in database yet.")
        return

    def on_tournament_change(e):
        state["tournament_id"] = tournaments.get(e.value)

    tournament_select = ui.select(
        options=list(tournaments.keys()),
        label="Tournament",
        on_change=on_tournament_change,
    ).classes("w-96")

    budget_input = ui.number("Budget", value=1000, min=0).classes("w-48")
    page_size_select = ui.select([10, 25, 50, 100, 250], value=25, label="Rows per page").classes("w-48")

    with ui.row():
        ui.button("Generate lineups", on_click=generate_lineups_action)
        ui.button("Previous", on_click=prev_page)
        ui.button("Next", on_click=next_page)

    page_label = ui.label("No lineups yet").classes("mt-2")

    columns = [
        {"name": "rank", "label": "#", "field": "rank"},
        {"name": "players", "label": "Players", "field": "players"},
        {"name": "teams", "label": "Teams", "field": "teams"},
        {"name": "total_cost", "label": "Cost", "field": "total_cost"},
        {"name": "total_rating", "label": "Total Rating", "field": "total_rating"},
    ]

    table = ui.table(columns=columns, rows=[]).classes("w-full mt-4")

@ui.page('/admin')
def admin_page():
    ui.label("Admin Panel").classes("text-2xl font-bold mb-4")

    with ui.tabs() as tabs:
        tab_teams = ui.tab('Teams')
        tab_players = ui.tab('Players')
        tab_tournaments = ui.tab('Tournaments')

    with ui.tab_panels(tabs, value=tab_teams):

        # ========================
        # TEAMS
        # ========================
        with ui.tab_panel(tab_teams):
            ui.label("Add Team")

            name_input = ui.input("Team name")

            def add_team():
                with SessionLocal() as session:
                    team = Team(name=name_input.value)
                    session.add(team)
                    session.commit()
                ui.notify("Team added")
                refresh_teams()

            ui.button("Add Team", on_click=add_team)

            team_table = ui.table(columns=[
                {"name": "id", "label": "ID", "field": "id"},
                {"name": "name", "label": "Name", "field": "name"},
            ], rows=[])

            def refresh_teams():
                with SessionLocal() as session:
                    teams = session.scalars(select(Team)).all()
                    team_table.rows = [{"id": t.id, "name": t.name} for t in teams]

            refresh_teams()

        # ========================
        # PLAYERS
        # ========================
        with ui.tab_panel(tab_players):
            ui.label("Add Player")

            with SessionLocal() as session:
                teams = session.scalars(select(Team)).all()

            team_options = {t.name: t.id for t in teams}

            name_input = ui.input("Player name")
            team_select = ui.select(options=list(team_options.keys()), label="Team")
            rating_input = ui.number("Rating", value=100)
            price_input = ui.number("Price", value=200)

            def add_player():
                with SessionLocal() as session:
                    team_id = team_options.get(team_select.value)

                    player = Player(
                        name=name_input.value,
                        team_id=team_id,
                        rating=rating_input.value,
                        price=price_input.value,
                    )
                    session.add(player)
                    session.commit()

                ui.notify("Player added")
                refresh_players()

            ui.button("Add Player", on_click=add_player)

            player_table = ui.table(columns=[
                {"name": "name", "label": "Name", "field": "name"},
                {"name": "team", "label": "Team", "field": "team"},
                {"name": "rating", "label": "Rating", "field": "rating"},
                {"name": "price", "label": "Price", "field": "price"},
            ], rows=[])

            def refresh_players():
                with SessionLocal() as session:
                    players = session.scalars(select(Player)).all()
                    rows = []
                    for p in players:
                        rows.append({
                            "name": p.name,
                            "team": p.team.name if p.team else "",
                            "rating": p.rating,
                            "price": p.price
                        })
                    player_table.rows = rows

            refresh_players()

        # ========================
        # TOURNAMENTS
        # ========================
        with ui.tab_panel(tab_tournaments):
            ui.label("Add Tournament")

            name_input = ui.input("Tournament name")
            format_input = ui.select(
                ["swiss", "single", "double", "group_double"],
                label="Format"
            )
            num_teams_input = ui.number("Number of teams", value=16)
            bo5_input = ui.checkbox("Has BO5 final")

            def add_tournament():
                with SessionLocal() as session:
                    tournament = Tournament(
                        name=name_input.value,
                        format_type=format_input.value,
                        num_teams=num_teams_input.value,
                        has_bo5_final=bo5_input.value,
                    )
                    session.add(tournament)
                    session.commit()

                ui.notify("Tournament added")
                refresh_tournaments()

            ui.button("Add Tournament", on_click=add_tournament)

            tournament_table = ui.table(columns=[
                {"name": "name", "label": "Name", "field": "name"},
                {"name": "format", "label": "Format", "field": "format"},
                {"name": "teams", "label": "Teams", "field": "teams"},
            ], rows=[])

            def refresh_tournaments():
                with SessionLocal() as session:
                    tournaments = session.scalars(select(Tournament)).all()
                    rows = []
                    for t in tournaments:
                        rows.append({
                            "name": t.name,
                            "format": t.format_type,
                            "teams": t.num_teams
                        })
                    tournament_table.rows = rows

            refresh_tournaments()

#app = ui.run_with(app=None)
ui.run()