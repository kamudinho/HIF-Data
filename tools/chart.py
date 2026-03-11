import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from PIL import Image
import requests
from io import BytesIO
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def get_logo(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None

def fetch_wyscout_data():
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    
    # Vi henter specifikt de kolonner, du har i din tabel
    query = """
    SELECT 
        TEAM_WYID, COMPETITION_WYID, MATCHES,
        GOALS, SHOTS, XGSHOT as XG, 
        PASSES, SUCCESSFULPASSES,
        DEFENSIVEDUELS, DEFENSIVEDUELSWON,
        INTERCEPTIONS, TOUCHINBOX
    FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL
    WHERE SEASON_WYID = 188330 
    AND COMPETITION_WYID = 328
    """
    df_res = conn.query(query)
    return pd.DataFrame(df_res)

def vis_side(*args, **kwargs):
    
    if "wyscout_stats_1div" not in st.session_state:
        with st.spinner("Henter data fra Snowflake..."):
            st.session_state["wyscout_stats_1div"] = fetch_wyscout_data()
    
    df = st.session_state["wyscout_stats_1div"].copy()

    # 1. Filtrer dropdown (Hvidovre, OB, etc. fra 1. Division)
    hold_1div = [navn for navn, info in TEAMS.items() if info.get("league") == "1. Division"]
    valgt_hold = st.selectbox("Vælg hold til analyse:", sorted(hold_1div))
    
    team_info = TEAMS[valgt_hold]
    team_wyid = int(team_info['team_wyid'])

    if df.empty:
        st.error("Kunne ikke finde data for COMPETITION_WYID 328.")
        return

    # 2. Beregn stats pr. kamp (Normalisering)
    # Vi bruger de præcise navne fra dit data-dump
    df['GOALS_PG'] = df['GOALS'] / df['MATCHES']
    df['SHOTS_PG'] = df['SHOTS'] / df['MATCHES']
    df['XG_PG'] = df['XG'] / df['MATCHES']
    df['PASSES_PG'] = df['PASSES'] / df['MATCHES']
    df['PASS_ACC'] = (df['SUCCESSFULPASSES'] / df['PASSES']) * 100
    df['DEF_DUELS_PG'] = df['DEFENSIVEDUELS'] / df['MATCHES']
    df['INTERCEPT_PG'] = df['INTERCEPTIONS'] / df['MATCHES']
    df['TOUCHBOX_PG'] = df['TOUCHINBOX'] / df['MATCHES']

    # 3. Find det valgte holds data
    target_team = df[df['TEAM_WYID'] == team_wyid]

    if target_team.empty:
        st.warning(f"Ingen data fundet for {valgt_hold} (ID: {team_wyid}) i 1. Division.")
        return

    # 4. Definition af Metrics til Pizza Chart
    metrics_map = [
        ('GOALS_PG', 'Mål', '#2ecc71'),
        ('XG_PG', 'xG', '#2ecc71'),
        ('SHOTS_PG', 'Skud', '#2ecc71'),
        ('TOUCHBOX_PG', 'Felt-aktioner', '#2ecc71'),
        ('PASSES_PG', 'Afleveringer', '#f1c40f'),
        ('PASS_ACC', 'Afleverings %', '#f1c40f'),
        ('DEF_DUELS_PG', 'Def. Dueller', '#e74c3c'),
        ('INTERCEPT_PG', 'Erobringer', '#e74c3c')
    ]

    labels, values, colors = [], [], []
    
    for col, label, color in metrics_map:
        # Beregn percentil sammenlignet med de andre hold i ligaen
        p_val = stats.percentileofscore(df[col].dropna(), target_team[col].values[0])
        labels.append(label)
        values.append(p_val)
        colors.append(color)

    # 5. Plotting
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#0E1117') # Streamlit mørk baggrund
    ax.set_facecolor('#0E1117')
    
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values += values[:1] # Luk cirklen
    angles += angles[:1]
    
    # Bar chart (Pizza slices)
    ax.bar(angles[:-1], values[:-1], width=(2*np.pi/len(labels))-0.1, 
           color=colors, alpha=0.6, edgecolor='white', linewidth=1.5)

    # Tilføj logo i midten
    logo_img = get_logo(team_info['logo'])
    if logo_img:
        imagebox = OffsetImage(logo_img, zoom=0.5)
        ab = AnnotationBbox(imagebox, (0, 0), frameon=False)
        ax.add_artist(ab)

    # Styling af labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color='white', size=12, fontweight='bold')
    ax.set_yticklabels([]) # Skjul 0-100 skalaen for et renere look
    ax.grid(color='grey', linestyle='--', alpha=0.3)

    st.pyplot(fig)

    # 6. Tabel med rå tal
    st.write(f"### Nøgletal for {valgt_hold} (Pr. kamp)")
    stats_cols = st.columns(3)
    stats_cols[0].metric("Mål", f"{target_team['GOALS_PG'].values[0]:.2f}")
    stats_cols[1].metric("xG", f"{target_team['XG_PG'].values[0]:.2f}")
    stats_cols[2].metric("Pass %", f"{target_team['PASS_ACC'].values[0]:.1f}%")

if __name__ == "__main__":
    vis_side()
