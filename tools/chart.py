import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from PIL import Image
import requests
from io import BytesIO
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn

def get_logo(url):
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None

def fetch_team_performance_data():
    conn = _get_snowflake_conn()
    
    # Din optimerede query med Standings join
    query = """
    SELECT DISTINCT 
        tm.TEAMNAME,
        s.SEASONNAME,
        tm.IMAGEDATAURL,
        t.GOALS, 
        t.XGSHOT, 
        t.CONCEDEDGOALS,
        t.XGSHOTAGAINST, 
        t.SHOTS, 
        t.PPDA,
        t.PASSESTOFINALTHIRD,
        t.FORWARDPASSES, 
        t.SUCCESSFULPASSESTOFINALTHIRD,
        st.TOTALPOINTS,
        st.TOTALPLAYED AS MATCHES,
        st.TOTALWINS,
        st.TOTALDRAWS,
        st.TOTALLOSSES,
        t.TEAM_WYID
    FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL AS t
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS AS s ON t.SEASON_WYID = s.SEASON_WYID
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS AS tm ON t.TEAM_WYID = tm.TEAM_WYID
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS_STANDINGS AS st 
        ON t.TEAM_WYID = st.TEAM_WYID AND t.SEASON_WYID = st.SEASON_WYID
    WHERE t.COMPETITION_WYID = 328
    AND s.SEASONNAME = '2025/2026'
    """
    df_res = conn.query(query)
    df = pd.DataFrame(df_res)
    
    if not df.empty:
        df.columns = [c.lower() for c in df.columns]
        df['team_wyid'] = pd.to_numeric(df['team_wyid']).astype(int)
    return df

def vis_side(*args, **kwargs):

    if "team_perf_stats" not in st.session_state:
        with st.spinner("Henter performance data..."):
            st.session_state["team_perf_stats"] = fetch_team_performance_data()
    
    df = st.session_state["team_perf_stats"].copy()

    if df.empty:
        st.error("Kunne ikke finde data for 1. Division 2025/2026.")
        return

    # 1. Holdvalg
    hold_1div = [navn for navn, info in TEAMS.items() if info.get("league") == "1. Division"]
    valgt_hold = st.selectbox("Vælg hold:", sorted(hold_1div))
    
    team_info = TEAMS[valgt_hold]
    team_wyid = int(team_info['team_wyid'])

    # 2. Beregninger (Normalisering pr. kamp)
    # Vi bruger 'matches' fra standings tabellen som nævner
    df['goals_pg'] = df['goals'] / df['matches']
    df['xg_pg'] = df['xgshot'] / df['matches']
    df['conceded_pg'] = df['concededgoals'] / df['matches']
    df['xg_against_pg'] = df['xgshotagainst'] / df['matches']
    df['shots_pg'] = df['shots'] / df['matches']
    df['pass_final_third_pg'] = df['passestofinalthird'] / df['matches']
    
    # PPDA er allerede et gennemsnit, så den skal ikke divideres
    # Men vi inverterer den til percentil-brug (lav PPDA = høj aggressivitet)
    df['pressing_intensity'] = 1 / df['ppda'] 

    # 3. Find target team
    target_team = df[df['team_wyid'] == team_wyid]
    if target_team.empty:
        st.warning(f"Ingen data fundet for {valgt_hold}.")
        return

    # 4. Pizza Chart setup
    metrics = [
        ('goals_pg', 'Mål', '#2ecc71'),
        ('xg_pg', 'xG', '#2ecc71'),
        ('shots_pg', 'Skud', '#2ecc71'),
        ('pass_final_third_pg', 'Felt-indlæg', '#f1c40f'),
        ('pressing_intensity', 'Pres (PPDA)', '#e74c3c'),
        ('xg_against_pg', 'xG Imod*', '#e74c3c') # Husk at lav score er bedst her
    ]

    labels, values, colors = [], [], []
    for col, label, color in metrics:
        # For xG Imod vil vi have at en LAV værdi giver en HØJ percentil (godt forsvar)
        if col == 'xg_against_pg':
            p_val = 100 - stats.percentileofscore(df[col], target_team[col].values[0])
        else:
            p_val = stats.percentileofscore(df[col], target_team[col].values[0])
        
        labels.append(label)
        values.append(p_val)
        colors.append(color)

    # 5. Plotting
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')
    
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    ax.bar(angles, values, width=0.7, color=colors, alpha=0.6, edgecolor='white')

    # Logo
    logo = get_logo(team_info['logo'])
    if logo:
        ax.add_artist(AnnotationBbox(OffsetImage(logo, zoom=0.4), (0, 0), frameon=False))

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color='white', size=11, fontweight='bold')
    ax.set_yticklabels([])
    ax.grid(color='grey', linestyle='--', alpha=0.3)
    st.pyplot(fig)

    # 6. Standings Info (Nyt pga. din nye query!)
    st.write("---")
    c1, c2, c3, c4 = st.columns(4)
    row = target_team.iloc[0]
    c1.metric("Point", int(row['totalpoints']))
    c2.metric("Vundne", int(row['totalwins']))
    c3.metric("Uafgjorte", int(row['totaldraws']))
    c4.metric("Tabte", int(row['totallosses']))

if __name__ == "__main__":
    vis_side()
