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
    """Henter de avancerede team-stats fra Snowflake"""
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    
    # Vi bruger dine gemte værdier: 2025/2026 og NordicBet Liga (328)
    query = """
    SELECT * FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL
    WHERE SEASON_WYID = 188330 
    AND COMPETITION_WYID = 328
    """
    df = conn.query(query)
    return pd.DataFrame(df)

def vis_side(analysis_package=None):
    st.title("📊 Holdprofil & Performance")

    # 1. Load Data
    if "wyscout_stats" not in st.session_state:
        with st.spinner("Henter performance-data..."):
            st.session_state["wyscout_stats"] = fetch_wyscout_data()
    
    df_raw = st.session_state["wyscout_stats"]

    # 2. Vælg Hold
    hold_navne = sorted(list(TEAMS.keys()))
    valgt_hold = st.selectbox("Vælg hold til analyse:", hold_navne)
    
    team_info = TEAMS[valgt_hold]
    team_wyid = team_info['team_wyid']
    primary_color = TEAM_COLORS.get(valgt_hold, {}).get("primary", "#df003b")

    # 3. Data Behandling
    df = df_raw.copy()
    # Konverter relevante kolonner til tal og divider med kampe (undtagen procenter/PPDA)
    metrics_to_normalize = [col for col in df.columns if col not in ['TEAM_WYID', 'MATCHES', 'PPDA', 'PASSESACC']]
    for col in metrics_to_normalize:
        df[col] = pd.to_numeric(df[col], errors='coerce') / df['MATCHES']

    target_team = df[df['TEAM_WYID'] == team_wyid]

    if target_team.empty:
        st.error(f"Ingen data fundet for {valgt_hold} i denne sæson.")
        return

    # 4. Definition af Metrics (Match dine Snowflake kolonnenavne her)
    # Format: (Kolonne, Display Navn, Kategori-farve)
    metrics_config = [
        ('GOALS', 'Mål', '#2ecc71'),
        ('SHOTS', 'Skud', '#2ecc71'),
        ('XG', 'xG', '#2ecc71'),
        ('PASSES', 'Afleveringer', '#f1c40f'),
        ('PASSESACC', 'Afleverings %', '#f1c40f'),
        ('DEFENSIVEDUELS', 'Def. Dueller', '#e74c3c'),
        ('INTERCEPTIONS', 'Erobringer', '#e74c3c'),
        ('PPDA', 'PPDA (Pres)', '#e74c3c')
    ]

    plot_labels, values, colors = [], [], []
    for col, label, color in metrics_config:
        if col in df.columns:
            p_val = stats.percentileofscore(df[col].dropna(), target_team[col].values[0])
            # Vend logikken for PPDA (lav er bedre)
            if col == 'PPDA': p_val = 100 - p_val
            
            plot_labels.append(label)
            values.append(p_val)
            colors.append(color)

    # 5. Plotting
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')
    
    num_vars = len(plot_labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)
    
    # Skiver (Percentiler)
    bars = ax.bar(angles, values, width=(2*np.pi/num_vars), bottom=25, 
                  color=colors, alpha=0.9, edgecolor='white', linewidth=2)

    # Logo i midten
    logo_img = get_logo(team_info['logo'])
    if logo_img:
        imagebox = OffsetImage(logo_img, zoom=0.6)
        ab = AnnotationBbox(imagebox, (0, 0), frameon=False)
        ax.add_artist(ab)

    # Labels og styling
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.axis('off')

    for angle, label in zip(angles, plot_labels):
        ax.text(angle, 135, label, size=11, color='white', fontweight='bold', ha='center')

    # Vis i Streamlit
    st.pyplot(fig)
    
    # Tabel-oversigt nedenunder
    st.write(f"### Nøgletal for {valgt_hold}")
    st.dataframe(target_team[ [m[0] for m in metrics_config] ])

if __name__ == "__main__":
    vis_side()
