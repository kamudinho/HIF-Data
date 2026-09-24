import dash
from dash import dcc, html, callback, Output, Input, State
import dash_bootstrap_components as dbc
import pandas as pd
import logging
import os
import sys
import numpy as np

# Konfigurer logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, '/assets/styles.css'],
                suppress_callback_exceptions=True)
server = app.server

# --- IMPORT AF MODULER ---
try:
    from components.header import build_header_layout
    import pages.kampoversigt
    import pages.player_stats
    import pages.team_stats
    import pages.dataoversigt
    import pages.team_matches
    import pages.top5
    import pages.kpi
    import pages.data_viz
    import pages.player_score
    logger.debug("Alle sider og header importeret succesfuldt.")
except ImportError as e:
    logger.error(f"FEJL ved import af moduler: {e}", exc_info=True)

# --- GLOBALE KONSTANTER & HOLD-VALG ---
ACTIVE_SEASON = "2026/2027"
ACTIVE_COMPETITION = "NordicBet Liga"
TEAM_WYID = 7490

# Dropdown-muligheder for Hvidovre IF setup
team_dropdown_options = [
    {'label': 'Hvidovre IF', 'value': 7490},
]

dcc_stores = html.Div([
    dcc.Store(id='players-data'),
    dcc.Store(id='playermatches-data'),
    dcc.Store(id='all-matches-data'),
    dcc.Store(id='all-teams-stats-data'),
    dcc.Store(id='events-data'),
], style={'display': 'none'})

# --- APP LAYOUT MED TOPMENU ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc_stores,
    build_header_layout(team_dropdown_options),  # Topmenu / Header placeret øverst
    html.Div(id='page-content', className="page-content", style={"padding": "20px"}),
], style={"min-height": "100vh", "backgroundColor": "#FFFFFF"})


@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname'),
     Input('team-dropdown', 'value')]
)
def display_page(pathname, selected_team):
    logger.debug(f"display_page kaldes for path: {pathname}, team: {selected_team}")

    try:
        if pathname == '/player-stats':
            return pages.player_stats.generate_player_stats_layout()
        elif pathname == '/team-stats':
            return pages.team_stats.generate_team_stats_layout()
        elif pathname == '/kampoversigt':
            return pages.kampoversigt.generate_match_stats(selected_team)
        elif pathname == '/top5':
            return pages.top5.generate_top5_layout(selected_team)
        elif pathname == '/dataoversigt':
            return pages.dataoversigt.generate_dataoversigt_layout(selected_team)
        elif pathname == '/kpi':
            return pages.kpi.generate_kpi_layout(selected_team)
        else:
            return html.Div([
                html.H3("Hvidovre IF - Match & Performance Dashboard"),
                html.P(f"Aktiv sæson: {ACTIVE_SEASON} | Turnering: {ACTIVE_COMPETITION}"),
                html.P("Brug topmenuen til at navigere mellem siderne.")
            ])
    except Exception as e:
        logger.error(f"Fejl ved routing til {pathname}: {e}", exc_info=True)
        return html.Div([html.H3(f"Fejl ved indlæsning af side: {pathname}")])


if __name__ == '__main__':
    app.run_server(debug=True)
