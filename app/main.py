from math import ceil
from sqlalchemy import select
from nicegui import ui

from app.models import Tournament
from app.services.lineups import get_players_for_tournament, generate_valid_lineups

from app.models import Team, Player, Tournament

from app.pages import home, admin  # noqa: F401

ui.run()