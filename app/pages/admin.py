from nicegui import ui
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Team, Player, Tournament

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

            name_input = ui.input(label="Team name")

            def add_team():
                team_name = (name_input.value or "").strip()
                if not team_name:
                    ui.notify("Team name cannot be empty", type="negative")
                    return

                with SessionLocal() as session:
                    team = Team(name=team_name)
                    session.add(team)
                    session.commit()

                ui.notify("Team added", type="positive")
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

            name_input = ui.input(label="Player name")
            team_select = ui.select(options=list(team_options.keys()), label="Team")
            rating_input = ui.number(label="Rating", value=100)
            price_input = ui.number(label="Price", value=200)

            def add_player():
                player_name = (name_input.value or "").strip()
                if not player_name:
                    ui.notify("Player name cannot be empty", type="negative")
                    return
                with SessionLocal() as session:
                    team_id = team_options.get(team_select.value)

                    player = Player(
                        name=player_name,
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

            name_input = ui.input(label="Tournament name")
            format_input = ui.select(
                ["swiss", "single", "double", "group_double"],
                label="Format"
            )
            num_teams_input = ui.number(label="Number of teams", value=16)
            bo5_input = ui.checkbox(label="Has BO5 final")

            def add_tournament():
                tournament_name = (name_input.value or "").strip()
                if not tournament_name:
                    ui.notify("Tournament name cannot be empty", type="negative")
                    return
                with SessionLocal() as session:
                    tournament = Tournament(
                        name=tournament_name,
                        format_type=format_input.value,
                        num_teams=num_teams_input.value,
                        has_bo5_final=bo5_input.value,
                    )
                    session.add(tournament)
                    session.commit()

                ui.notify("Tournament added", type="positive")
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
