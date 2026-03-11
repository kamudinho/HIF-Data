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
    """Henter data specifikt for 1. Division (NordicBet Liga)"""
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    
    # 328 er NordicBet Ligaen jf. dine indstillinger
    query = """
    SELECT * FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL
    WHERE SEASON_WYID = 188330 
    AND COMPETITION_WYID = 328
    """
    df_res = conn.query(query)
    return pd.DataFrame(df_res)

def vis_side(analysis_package=None):
    st.title("📊 1. Division: Performance Profiler")

    # 1. Load Data
    if "wyscout_stats_1div" not in st.session_state:
        with st.spinner("Henter data for 1. Division..."):
            st.session_state["wyscout_stats_1div"] = fetch_wyscout_data()
    
    df_raw = st.session_state["wyscout_stats_1div"]

    # 2. Filtrer dropdown til kun at vise hold fra 1. Division
    # Vi kigger i din TEAMS mapping og tager kun dem hvor league == "1. Division"
    hold_1div = [navn for navn, info in TEAMS.items() if info.get("league") == "1. Division"]
    valgt_hold = st.selectbox("Vælg hold fra 1. Division:", sorted(hold_1div))
    
    team_info = TEAMS[valgt_hold]
    team_wyid = team_info['team_wyid']

    # 3. Data Behandling
    df = df_raw.copy()
    if df.empty:
        st.error("Ingen data fundet i Snowflake for 1. Division (ID: 328).")
        return

    # Normalisering (Metrics pr. kamp)
    # Vi sikrer os at kolonnenavnene er UPPERCASE som i Snowflake
    metrics_to_normalize = [col for col in df.columns if col not in ['TEAM_WYID', 'MATCHES', 'PPDA', 'PASSESACC']]
    for col in metrics_to_normalize:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce') / df['MATCHES']

    target_team = df[df['TEAM_WYID'] == team_wyid]

    if target_team.empty:
        st.warning(f"Holdet {valgt_hold} blev ikke fundet i de hentede data (WYID: {team_wyid}).")
        # debug info hvis nødvendigt: st.write(df['TEAM_WYID'].unique())
        return

    # 4. Pizza Chart Konfiguration
    metrics_config = [
        ('GOALS', 'Mål', '#2ecc71'),
        ('SHOTS', 'Skud', '#2ecc71'),
        ('XG', 'xG', '#2ecc71'),
        ('PASSES', 'Afleveringer', '#f1c40f'),
        ('PASSESACC', 'Afleverings %', '#f1c40f'),
        ('DEFENSIVEDUELS', 'Def. Dueller', '#e74c3c'),
        ('INTERCEPTIONS', 'Erobringer', '#e74c3c')
    ]

    plot_labels, values, colors = [], [], []
    for col, label, color in metrics_config:
        if col in df.columns:
            p_val = stats.percentileofscore(df[col].dropna(), target_team[col].values[0])
            plot_labels.append(label)
            values.append(p_val)
            colors.append(color)

    # 5. Visualisering
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')
    
    num_vars = len(plot_labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)
    
    ax.bar(angles, values, width=(2*np.pi/num_vars), bottom=25, 
           color=colors, alpha=0.9, edgecolor='white', linewidth=2)

    logo_img = get_logo(team_info['logo'])
    if logo_img:
        imagebox = OffsetImage(logo_img, zoom=0.6)
        ab = AnnotationBbox(imagebox, (0, 0), frameon=False)
        ax.add_artist(ab)

    ax.axis('off')
    for angle, label in zip(angles, plot_labels):
        ax.text(angle, 135, label, size=11, color='white', fontweight='bold', ha='center')

    st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
