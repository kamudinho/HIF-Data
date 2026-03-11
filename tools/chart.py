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
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None

def fetch_team_data():
    conn = _get_snowflake_conn()
    
    # Vi bruger store bogstaver i WHERE-clausen for at matche Snowflake standard
    # Og vi sikrer os, at tallene ikke er i anførselstegn, hvis kolonnen er numerisk
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
    
    if df.empty:
        return df

    # Tving kolonner til små bogstaver for nemmere håndtering i Python
    df.columns = [c.lower() for c in df.columns]
    
    # Sikr at ID er heltal
    df['team_wyid'] = pd.to_numeric(df['team_wyid']).astype(int)
    return df

def vis_side(*args, **kwargs):
    # Ingen subheader her - direkte til titlen

    if "team_stats_1div" not in st.session_state:
        with st.spinner("Henter data..."):
            st.session_state["team_stats_1div"] = fetch_team_data()
    
    df = st.session_state["team_stats_1div"].copy()

    if df.empty:
        st.error("Fejl: Ingen rækker fundet i Snowflake (SEASON 188330, COMP 328).")
        # Knap til at tvinge genindlæsning hvis data er blevet opdateret
        if st.button("Prøv at genindlæse data"):
            st.session_state.pop("team_stats_1div")
            st.rerun()
        return

    # 1. Valg af hold
    hold_1div = [navn for navn, info in TEAMS.items() if info.get("league") == "1. Division"]
    valgt_hold = st.selectbox("Vælg hold:", sorted(hold_1div))
    
    team_info = TEAMS[valgt_hold]
    team_wyid = int(team_info['team_wyid'])

    # 2. Beregninger (PG = Per Game)
    # Vi bruger fillna(0) for at undgå fejl ved division med nul
    df['goals_pg'] = df['goals'] / df['matches'].replace(0, np.nan)
    df['xg_pg'] = df['xgshot'] / df['matches'].replace(0, np.nan)
    df['shots_pg'] = df['shots'] / df['matches'].replace(0, np.nan)
    df['passes_pg'] = df['passes'] / df['matches'].replace(0, np.nan)
    df['pass_acc'] = (df['successfulpasses'] / df['passes'].replace(0, np.nan)) * 100
    df['def_duels_pg'] = df['defensiveduels'] / df['matches'].replace(0, np.nan)
    df['intercept_pg'] = df['interceptions'] / df['matches'].replace(0, np.nan)
    df['touchbox_pg'] = df['touchinbox'] / df['matches'].replace(0, np.nan)
    df = df.fillna(0)

    # 3. Find det valgte hold
    target_team = df[df['team_wyid'] == team_wyid]

    if target_team.empty:
        st.warning(f"Holdet '{valgt_hold}' (ID: {team_wyid}) findes ikke i datasættet.")
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

    logo = get_logo(team_info['logo'])
    if logo:
        ax.add_artist(AnnotationBbox(OffsetImage(logo, zoom=0.4), (0, 0), frameon=False))

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color='white', size=11, fontweight='bold')
    ax.set_yticklabels([])
    ax.grid(color='grey', linestyle='--', alpha=0.3)
    
    st.pyplot(fig)

    # 6. Tabelvisning (uden subheader)
    st.dataframe(
        target_team[['matches', 'goals_pg', 'xg_pg', 'pass_acc', 'touchbox_pg']],
        use_container_width=True
    )
