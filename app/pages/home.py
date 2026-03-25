from nicegui import ui

from app.services.utils import load_tournaments, refresh_table, generate_lineups_action
from sqlalchemy import select

@ui.page("/")
def home_page():
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
