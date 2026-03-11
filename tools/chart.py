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

# Vi bruger kun din rå database-forbindelse
from data.data_load import _get_snowflake_conn

def get_logo(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None

def fetch_team_data():
    conn = _get_snowflake_conn()
    # Her bruger vi din specifikke tabelstier fra din wy_queries.py
    query = """
    SELECT 
        TEAM_WYID, 
        MATCHES,
        GOALS, 
        SHOTS, 
        XGSHOT, 
        PASSES, 
        SUCCESSFULPASSES,
        DEFENSIVEDUELS, 
        INTERCEPTIONS, 
        TOUCHINBOX
    FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL
    WHERE SEASON_WYID = 188330 
    AND COMPETITION_WYID = 328
    """
    df_res = conn.query(query)
    df = pd.DataFrame(df_res)
    
    # VIKTIGT: Snowflake returnerer UPPERCASE. 
    # Vi tvinger dem til små bogstaver her, så resten af koden er nem at skrive.
    df.columns = [c.lower() for c in df.columns]
    return df

def vis_side(*args, **kwargs):

    if "team_stats_1div" not in st.session_state:
        with st.spinner("Henter liga-data..."):
            st.session_state["team_stats_1div"] = fetch_team_data()
    
    df = st.session_state["team_stats_1div"].copy()

    # 1. Valg af hold
    hold_1div = [navn for navn, info in TEAMS.items() if info.get("league") == "1. Division"]
    valgt_hold = st.selectbox("Vælg hold:", sorted(hold_1div))
    
    team_info = TEAMS[valgt_hold]
    # Vi sikrer os at ID er en int, da Snowflake returnerer tal for ID kolonner
    team_wyid = int(team_info['team_wyid'])

    if df.empty:
        st.error("Ingen data fundet i Snowflake for Liga 328.")
        return

    # 2. Beregninger (Nu med små bogstaver pga. fixet i fetch_team_data)
    df['goals_pg'] = df['goals'] / df['matches']
    df['xg_pg'] = df['xgshot'] / df['matches']
    df['shots_pg'] = df['shots'] / df['matches']
    df['passes_pg'] = df['passes'] / df['matches']
    df['pass_acc'] = (df['successfulpasses'] / df['passes']) * 100
    df['def_duels_pg'] = df['defensiveduels'] / df['matches']
    df['intercept_pg'] = df['interceptions'] / df['matches']
    df['touchbox_pg'] = df['touchinbox'] / df['matches']

    # 3. Find det valgte hold
    target_team = df[df['team_wyid'] == team_wyid]

    if target_team.empty:
        st.warning(f"Data for ID {team_wyid} ikke fundet i tabellen.")
        return

    # 4. Pizza Chart setup
    metrics = [
        ('goals_pg', 'Mål', '#2ecc71'),
        ('xg_pg', 'xG', '#2ecc71'),
        ('shots_pg', 'Skud', '#2ecc71'),
        ('touchbox_pg', 'Felt-aktioner', '#2ecc71'),
        ('passes_pg', 'Passes', '#f1c40f'),
        ('pass_acc', 'Pass %', '#f1c40f'),
        ('def_duels_pg', 'Def. Dueller', '#e74c3c'),
        ('intercept_pg', 'Erobringer', '#e74c3c')
    ]

    labels, values, colors = [], [], []
    for col, label, color in metrics:
        p_val = stats.percentileofscore(df[col].dropna(), target_team[col].values[0])
        labels.append(label)
        values.append(p_val)
        colors.append(color)

    # 5. Plot (Pizza Chart)
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')
    
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    ax.bar(angles, values, width=0.7, color=colors, alpha=0.6, edgecolor='white')

    # Logo midt i chartet
    logo = get_logo(team_info['logo'])
    if logo:
        ab = AnnotationBbox(OffsetImage(logo, zoom=0.4), (0, 0), frameon=False)
        ax.add_artist(ab)

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color='white', size=10)
    ax.set_yticklabels([])
    
    st.pyplot(fig)

    # 6. Tabel
    st.table(target_team[['matches', 'goals_pg', 'xg_pg', 'pass_acc']])
