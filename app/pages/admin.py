from nicegui import ui
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models import Team, Player, Tournament, TournamentTeam

import asyncio

@ui.page('/admin')
def admin_page():
    ui.label("Admin Panel").classes("text-2xl font-bold mb-4")

    # =========================================================
    # TOURNAMENT WIZARD STATE + DIALOG
    # =========================================================
    selected_team_ids = []
    team_state = {}    # {team_id: {"ranking": ..., "points": ...}}
    player_state = {}  # {player_id: {"team_id": ..., "rating": ..., "price": ...}}

    with ui.dialog() as tournament_dialog:
        with ui.card().classes("w-[1100px] max-w-full h-[90vh] flex flex-col"):
            ui.label("Create Tournament").classes("text-xl font-bold mb-2")

            # -------------------------
            # SCROLLABLE CONTENT
            # -------------------------
            with ui.column().classes("flex-1 overflow-auto"):

                with ui.tabs() as tournament_tabs:
                    tab_info = ui.tab("Tournament info")
                    tab_teams = ui.tab("Teams")
                    tab_players = ui.tab("Players")

                with ui.tab_panels(tournament_tabs, value=tab_info).classes("w-full"):
                    # -------------------------
                    # STEP 1: TOURNAMENT INFO
                    # -------------------------
                    with ui.tab_panel(tab_info):
                        tournament_name_input = ui.input(label="Tournament name").classes("w-full")

                        with ui.row().classes("mt-4"):
                            ui.button("Cancel", on_click=tournament_dialog.close)

                            async def go_to_team_step():
                                await asyncio.sleep(0)
                                name = (tournament_name_input.value or "").strip()
                                if not name:
                                    ui.notify("Tournament name cannot be empty", type="negative")
                                    return
                                tournament_tabs.value = tab_teams
                                render_team_step()

                            ui.button("Next", on_click=go_to_team_step)

                    # -------------------------
                    # STEP 2: PICK + EDIT TEAMS
                    # -------------------------
                    with ui.tab_panel(tab_teams):
                        ui.label("Select teams participating in this tournament").classes("text-lg font-semibold mb-2")

                        team_selection_container = ui.column().classes("w-full gap-4")

                        def ensure_team_state(team):
                            if team.id not in team_state:
                                team_state[team.id] = {
                                    "ranking": team.hltv_ranking if team.hltv_ranking is not None else 0,
                                    "points": team.hltv_points if team.hltv_points is not None else 0,
                                }

                        def toggle_team(team_id: int):
                            if team_id in selected_team_ids:
                                selected_team_ids.remove(team_id)

                                # remove player state for removed team
                                for pid in list(player_state.keys()):
                                    if player_state[pid]["team_id"] == team_id:
                                        del player_state[pid]
                            else:
                                selected_team_ids.append(team_id)

                            render_team_step()

                        def render_team_step():
                            team_selection_container.clear()

                            with team_selection_container:
                                # all teams as click-to-select buttons
                                ui.label("Click a team to add/remove it").classes("font-medium")
                                with ui.row().classes("w-full gap-2"):
                                    with SessionLocal() as session:
                                        teams = session.scalars(select(Team).order_by(Team.name)).all()

                                    for team in teams:
                                        is_selected = team.id in selected_team_ids
                                        label = f"✓ {team.name}" if is_selected else team.name
                                        btn = ui.button(label, on_click=lambda tid=team.id: toggle_team(tid))
                                        if is_selected:
                                            btn.props("unelevated color=primary")
                                        else:
                                            btn.props("outline")

                                ui.separator()
                                ui.label("Selected teams").classes("text-lg font-semibold")

                                if not selected_team_ids:
                                    ui.label("No teams selected yet.")
                                else:
                                    with SessionLocal() as session:
                                        selected_teams = session.scalars(
                                            select(Team).where(Team.id.in_(selected_team_ids)).order_by(Team.name)
                                        ).all()

                                    for team in selected_teams:
                                        ensure_team_state(team)
                                        with ui.card().classes("w-full"):
                                            ui.label(team.name).classes("text-md font-bold")

                                            with ui.row().classes("w-full"):
                                                hltv_ranking_input = ui.number(
                                                    label="HLTV ranking",
                                                    value=team_state[team.id]["ranking"],
                                                ).classes("w-48")

                                                hltv_ranking_input.on_value_change(
                                                    lambda e, tid=team.id: team_state[tid].__setitem__(
                                                        "ranking", e.value if e.value is not None else 0
                                                    )
                                                )

                                                hltv_points_input = ui.number(
                                                    label="HLTV points",
                                                    value=team_state[team.id]["points"],
                                                ).classes("w-48")

                                                hltv_points_input.on_value_change(
                                                    lambda e, tid=team.id: team_state[tid].__setitem__(
                                                        "points", e.value if e.value is not None else 0
                                                    )
                                                )

                                                valve_ranking_input = ui.number(
                                                    label="Valve ranking",
                                                    value=team_state[team.id]["ranking"],
                                                ).classes("w-48")

                                                valve_ranking_input.on_value_change(
                                                    lambda e, tid=team.id: team_state[tid].__setitem__(
                                                        "ranking", e.value if e.value is not None else 0
                                                    )
                                                )

                                                valve_points_input = ui.number(
                                                    label="Valve points",
                                                    value=team_state[team.id]["points"],
                                                ).classes("w-48")

                                                valve_points_input.on_value_change(
                                                    lambda e, tid=team.id: team_state[tid].__setitem__(
                                                        "points", e.value if e.value is not None else 0
                                                    )
                                                )

                            # if we are already on the player step, refresh it too
                            if tournament_tabs.value == tab_players:
                                render_player_step()

                        with ui.row().classes("mt-4"):
                            async def back_to_info():
                                await asyncio.sleep(0)
                                tournament_tabs.value = tab_info

                            async def go_to_players_step():
                                await asyncio.sleep(0)
                                if not selected_team_ids:
                                    ui.notify("Select at least one team", type="negative")
                                    return
                                tournament_tabs.value = tab_players
                                render_player_step()

                            ui.button("Back", on_click=back_to_info)
                            ui.button("Next", on_click=go_to_players_step)

                    # -------------------------
                    # STEP 3: PICK + EDIT PLAYERS
                    # -------------------------
                    with ui.tab_panel(tab_players):
                        ui.label("Edit the players from the selected teams").classes("text-lg font-semibold mb-2")

                        player_selection_container = ui.column().classes("w-full gap-4")

                        def ensure_player_state(player):
                            if player.id not in player_state:
                                player_state[player.id] = {
                                    "team_id": player.team_id,
                                    "rating": player.rating,
                                    "price": player.price,
                                }

                        def render_player_step():
                            player_selection_container.clear()

                            with player_selection_container:
                                if not selected_team_ids:
                                    ui.label("No teams selected. Go back and select at least one team.")
                                    return

                                with SessionLocal() as session:
                                    players = session.scalars(
                                        select(Player)
                                        .options(selectinload(Player.team))
                                        .where(Player.team_id.in_(selected_team_ids))
                                        .order_by(Player.name)
                                    ).all()

                                if not players:
                                    ui.label("No players found for the selected teams.")
                                else:
                                    for player in players:
                                        ensure_player_state(player)

                                        team_name = player.team.name if player.team else ""

                                        with ui.card().classes("w-full"):
                                            ui.label(f"{player.name} — {team_name}").classes("font-bold")

                                            with ui.row().classes("w-full"):
                                                rating_input = ui.number(
                                                    label="Rating",
                                                    value=player_state[player.id]["rating"],
                                                ).classes("w-48")

                                                rating_input.on_value_change(
                                                    lambda e, pid=player.id: player_state[pid].__setitem__(
                                                        "rating", e.value if e.value is not None else 0
                                                    )
                                                )

                                                price_input = ui.number(
                                                    label="Price",
                                                    value=player_state[player.id]["price"],
                                                ).classes("w-48")

                                                price_input.on_value_change(
                                                    lambda e, pid=player.id: player_state[pid].__setitem__(
                                                        "price", e.value if e.value is not None else 0
                                                    )
                                                )

                            # clean up any player states from removed teams
                            for pid in list(player_state.keys()):
                                if player_state[pid]["team_id"] not in selected_team_ids:
                                    del player_state[pid]

                        with ui.row().classes("mt-4"):
                            async def back_to_teams():
                                await asyncio.sleep(0)
                                tournament_tabs.value = tab_teams
                                render_team_step()

                            async def save_tournament():
                                await asyncio.sleep(0)

                                tournament_name = (tournament_name_input.value or "").strip()
                                if not tournament_name:
                                    ui.notify("Tournament name cannot be empty", type="negative")
                                    return

                                if not selected_team_ids:
                                    ui.notify("You must select at least one team", type="negative")
                                    return

                                with SessionLocal() as session:
                                    tournament = Tournament(name=tournament_name)
                                    session.add(tournament)
                                    session.flush()  # get tournament.id

                                    # save selected teams in tournament + update team fields
                                    teams = session.scalars(
                                        select(Team).where(Team.id.in_(selected_team_ids))
                                    ).all()

                                    for team in teams:
                                        state = team_state.get(team.id, {})
                                        team.hltv_ranking = int(state.get("ranking") or 0)
                                        team.hltv_points = int(state.get("points") or 0)

                                        session.add(TournamentTeam(
                                            tournament_id=tournament.id,
                                            team_id=team.id
                                        ))

                                    # update selected players
                                    players = session.scalars(
                                        select(Player).where(Player.team_id.in_(selected_team_ids))
                                    ).all()

                                    for player in players:
                                        state = player_state.get(player.id)
                                        if not state:
                                            continue
                                        player.rating = float(state.get("rating") or 0)
                                        player.price = int(state.get("price") or 0)

                                    session.commit()

                                ui.notify("Tournament created successfully", type="positive")
                                tournament_dialog.close()
                                refresh_teams()

                            ui.button("Back", on_click=back_to_teams)
                            ui.button("Save tournament", on_click=save_tournament).props("color=primary")

    def open_tournament_wizard():
        # reset wizard each time it opens
        tournament_name_input.value = ""
        selected_team_ids.clear()
        team_state.clear()
        player_state.clear()
        tournament_tabs.value = tab_info
        render_team_step()
        render_player_step()
        tournament_dialog.open()

    # ========================
    # DIALOG (MODAL)
    # ========================
    with ui.dialog() as team_dialog, ui.card():
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

            team_dialog.close()
            refresh_teams()

        with ui.row():
            ui.button("Cancel", on_click=team_dialog.close)
            ui.button("Create", on_click=submit_team_with_players)

    # ========================
    # BUTTON TO OPEN DIALOG
    # ========================
    ui.button("Add Team (with players)", on_click=team_dialog.open)
    ui.button("Create Tournament", on_click=open_tournament_wizard).props("color=primary")

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