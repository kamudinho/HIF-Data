import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn
# Vi bruger team_mapping for at låse til 1. division, nuværende sæson og hente logoer/farver
from data.utils.team_mapping import TEAMS, TEAM_COLORS, COMPETITIONS, TOURNAMENTCALENDAR_NAME

# --- 1. DATAHENTNING OG PROCESSERING ---

@st.cache_data(ttl=3600)
def load_position_viz_data():
    conn = _get_snowflake_conn()
    
    # Konfiguration fra team_mapping
    wyid = COMPETITIONS["1. Division"]["wyid"]
    season = TOURNAMENTCALENDAR_NAME # F.eks. "2025/2026"
    db = "KLUB_HVIDOVREIF.AXIS"
    
    # SQL: Henter gennemsnitlige hold-metrics for NordicBet Liga i den valgte sæson
    # Vi henter kun de metrics, vi vil vise i dropdownen
    query = f"""
        SELECT t.TEAMNAME, t.TEAM_WYID,
               AVG(adv.XG) as XG, AVG(adv.GOALS) as GOALS, AVG(adv.SHOTS) as SHOTS,
               AVG(md.INTERCEPTIONS) as INTERCEPTIONS, AVG(md.TACKLES) as TACKLES, 
               AVG(mp.PASSES) as PASSES, AVG(mp.PROGRESSIVEPASSES) as PROGRESSIVEPASSES
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = {wyid}
        AND tm.SEASONNAME = '{season}'
        GROUP BY t.TEAMNAME, t.TEAM_WYID
    """
    
    try:
        df = conn.query(query)
        # Sørg for at alle holdnavne og kolonnenavne er i overensstemmelse
        df.columns = [c.upper() for c in df.columns]
        
        # Mapping af logoer og farver baseret på holdnavnet
        logo_urls = []
        primary_colors = []
        
        for name in df['TEAMNAME']:
            # Find matchende hold i TEAMS mapping
            team_info = next((info for t_name, info in TEAMS.items() if t_name.lower() in name.lower() or name.lower() in t_name.lower()), {})
            logo_urls.append(team_info.get('logo', ""))
            
            # Find farve i TEAM_COLORS mapping (hvidovre er rød, andre mørkeblå som standard)
            team_color = next((color_info for t_name, color_info in TEAM_COLORS.items() if t_name.lower() in name.lower() or name.lower() in t_name.lower()), {"primary": "#1b365d"})
            primary_colors.append(team_color.get("primary"))
            
        df['LOGO_URL'] = logo_urls
        df['COLOR'] = primary_colors
        return df
        
    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
        return pd.DataFrame()

# --- 2. HOVEDFUNKTION TIL VISNING ---

def vis_side():
    # Indlæs data
    df = load_position_viz_data()
    
    if df.empty:
        st.warning(f"Ingen data fundet for 1. Division i sæson {TOURNAMENTCALENDAR_NAME}.")
        return

    # --- DROP-DOWN TIL VALG AF METRIC ---
    metric_options = {
        'Total xG (Avg.)': 'XG',
        'Mål (Avg.)': 'GOALS',
        'Skud (Avg.)': 'SHOTS',
        'Interceptions (Avg.)': 'INTERCEPTIONS',
        'Tacklinger (Avg.)': 'TACKLES',
        'Afleveringer (Avg.)': 'PASSES',
        'Progressive Afleveringer (Avg.)': 'PROGRESSIVEPASSES'
    }
    
    c1, c2 = st.columns([1, 2]) # Placer dropdown i venstre side
    selected_label = c1.selectbox("Vælg Metric til visning", list(metric_options.keys()))
    selected_metric = metric_options[selected_label]

    # Sorter data efter den valgte metric for at placere dem pænt vertikalt
    # Det bedste hold i den valgte metric er øverst
    df_plot = df.sort_values(selected_metric, ascending=True).reset_index(drop=True)

    # --- DYNAMISK LOGO SCATTER PLOT ---
    fig = go.Figure()

    # Vi bruger y-aksen til at sprede logoerne ud vertikalt, så de ikke overlapper.
    # Selve den præstations-mæssige placering er kun på x-aksen.
    df_plot['Y_POS'] = list(range(len(df_plot)))

    for i, row in df_plot.iterrows():
        if row['LOGO_URL']:
            # Tilføj logo som markør
            fig.add_layout_image(
                dict(
                    source=row['LOGO_URL'],
                    xref="x", yref="y",
                    x=row[selected_metric], y=row['Y_POS'],
                    sizex=1, sizey=1, # Juster størrelsen på logoerne her
                    xanchor="center", yanchor="middle"
                )
            )

    # Tilføj usynlige scatter-punkter for at styre aksen, hover-tekst og farver (hvis du vil beholde hvidovre rød)
    fig.add_trace(go.Scatter(
        x=df_plot[selected_metric],
        y=df_plot['Y_POS'],
        mode='markers',
        marker=dict(size=25, opacity=0), # Usynlige markører
        hovertext=df_plot['TEAMNAME'],
        hovertemplate="<b>%{hovertext}</b><br>Værdi: %{x}<extra></extra>", # Ren hover, kun holdnavn og værdi
    ))

    # Konfiguration af layout
    fig.update_layout(
        title=dict(
            text=f"1. Division {TOURNAMENTCALENDAR_NAME} - Position Performance ({selected_label})",
            font=dict(size=18)
        ),
        height=600,
        margin=dict(l=50, r=50, t=60, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title=selected_label, 
            showgrid=True, 
            gridcolor="#eee", 
            zeroline=False
        ),
        yaxis=dict(
            title=None, 
            showticklabels=False, 
            showgrid=False, 
            zeroline=False,
            range=[-1, len(df_plot)]
        ),
        showlegend=False
    )

    # Vis grafen
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

if __name__ == "__main__":
    vis_side()
