from nicegui import ui
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Team, Player, Tournament

import asyncio

@ui.page('/admin')
def admin_page():
    ui.label("Admin Panel").classes("text-2xl font-bold mb-4")

    with ui.tab_panel(tab_teams):
    ui.label("Teams Management")

    # ========================
    # DIALOG (MODAL)
    # ========================
    with ui.dialog() as dialog, ui.card():
        ui.label("Add Team with Players").classes("text-xl font-bold")

        team_name_input = ui.input(label="Team name")

        player_inputs = []
        for i in range(5):
            player_inputs.append(ui.input(label=f"Player {i+1} name"))

        async def submit_team_with_players():
            await asyncio.sleep(0)

            team_name = (team_name_input.value or "").strip()
            player_names = [(p.value or "").strip() for p in player_inputs]

            # Validation
            if not team_name:
                ui.notify("Team name cannot be empty", type="negative")
                return

            if any(not name for name in player_names):
                ui.notify("All 5 player names are required", type="negative")
                return

            with SessionLocal() as session:
                # Create team
                team = Team(name=team_name)
                session.add(team)
                session.flush()  # get team.id before commit

                # Create players
                for name in player_names:
                    player = Player(
                        name=name,
                        team_id=team.id,
                        rating=0,
                        price=0,
                    )
                    session.add(player)

                session.commit()

            ui.notify("Team and players added!", type="positive")

            dialog.close()
            refresh_teams()
            refresh_players()

        with ui.row():
            ui.button("Cancel", on_click=dialog.close)
            ui.button("Create", on_click=submit_team_with_players)

    # ========================
    # BUTTON TO OPEN DIALOG
    # ========================
    ui.button("Add Team (with players)", on_click=dialog.open)

    # ========================
    # EXISTING TABLE
    # ========================
    team_table = ui.table(columns=[
        {"name": "id", "label": "ID", "field": "id"},
        {"name": "name", "label": "Name", "field": "name"},
    ], rows=[])

    def refresh_teams():
        with SessionLocal() as session:
            teams = session.scalars(select(Team)).all()
            team_table.rows = [{"id": t.id, "name": t.name} for t in teams]

    refresh_teams()