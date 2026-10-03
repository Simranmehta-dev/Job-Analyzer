"""Entry point:  panel serve app.py --show"""
from hiring_funnel.dashboard import create_app

create_app().servable()
