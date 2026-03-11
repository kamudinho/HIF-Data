import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from PIL import Image
import requests
from io import BytesIO
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from data.utils.team_mapping import TEAMS  # Behold denne til farver/navne

# Importér din eksisterende motor
from tools.scouting_tool import get_scouting_package 

def get_logo(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None

def vis_side(*args, **kwargs):
    st.title("📊 1. Division: Performance Profiler")

    # 1. Hent data via din eksisterende pakke
    if "scout_data" not in st.session_state:
        with st.spinner("Henter data fra Snowflake..."):
            # Vi bruger din eksisterende funktion
            st.session_state["scout_data"] = get_scouting_package()

    # Vi skal bruge de avancerede stats (Team stats skal findes i din pakke)
    # OBS: Hvis din get_scouting_package kun henter spiller-stats, 
    # skal vi sikre os at vi har hold-data. 
    # Her antager vi at 'advanced_stats' indeholder det nødvendige:
    df = st.session_state["scout_data"]["advanced_stats"].copy()

    if df.empty:
        st.error("Kunne ikke finde hold-data for 1. Division (ID 328).")
        return

    # 2. Dropdown til valg af hold (Fra din TEAMS mapping)
    hold_1div = [navn for navn, info in TEAMS.items() if info.get("league") == "1. Division"]
    valgt_hold = st.selectbox("Vælg hold til analyse:", sorted(hold_1div))
    
    team_info = TEAMS[valgt_hold]
    team_wyid = str(team_info['team_wyid']) # Din pakke caster ID til string

    # 3. Beregn stats (Håndterer UPPERCASE fra Snowflake)
    # Vi mapper dine Snowflake-kolonner til de beregnede felter
    try:
        # Normalisering pr. kamp (Husk: Snowflake = STORE BOGSTAVER)
        # Hvis dine team-stats ligger i en anden tabel, skal du sikre dig at kolonnenavne matcher:
        df['GOALS_PG'] = df['GOALS'] / df['MATCHES'] if 'GOALS' in df.columns else 0
        df['XG_PG'] = df['XGSHOT'] / df['MATCHES']
        df['SHOTS_PG'] = df['SHOTS'] / df['MATCHES'] if 'SHOTS' in df.columns else 0
        df['PASSES_PG'] = df['PASSES'] / df['MATCHES']
        df['PASS_ACC'] = (df['SUCCESSFULPASSES'] / df['PASSES']) * 100
        df['DEF_DUELS_PG'] = df['DUELS'] / df['MATCHES'] # Mapper DUELS til defensiv
        df['INTERCEPT_PG'] = df['INTERCEPTIONS'] / df['MATCHES']
        df['TOUCHBOX_PG'] = df['TOUCHINBOX'] / df['MATCHES']
    except Exception as e:
        st.error(f"Fejl i beregning af stats: {e}")
        st.info("Tjek om dine kolonnenavne i Snowflake matcher (f.eks. XGSHOT vs XG)")
        return

    # 4. Find det valgte holds data
    target_team = df[df['TEAM_WYID'] == team_wyid]

    if target_team.empty:
        st.warning(f"Ingen data fundet for {valgt_hold} (ID: {team_wyid}).")
        return

    # 5. Pizza Chart Metrics
    metrics_map = [
        ('GOALS_PG', 'Mål', '#2ecc71'),
        ('XG_PG', 'xG', '#2ecc71'),
        ('SHOTS_PG', 'Skud', '#2ecc71'),
        ('TOUCHBOX_PG', 'Felt-aktioner', '#2ecc71'),
        ('PASSES_PG', 'Afleveringer', '#f1c40f'),
        ('PASS_ACC', 'Afleverings %', '#f1c40f'),
        ('DEF_DUELS_PG', 'Dueller', '#e74c3c'),
        ('INTERCEPT_PG', 'Erobringer', '#e74c3c')
    ]

    labels, values, colors = [], [], []
    for col, label, color in metrics_map:
        # Percentil beregning mod de andre hold i listen
        p_val = stats.percentileofscore(df[col].dropna(), target_team[col].values[0])
        labels.append(label)
        values.append(p_val)
        colors.append(color)

    # 6. Plotting (Samme flotte look som før)
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')
    
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    plot_values = values + values[:1]
    plot_angles = angles + angles[:1]
    
    ax.bar(angles, values, width=(2*np.pi/len(labels))-0.1, 
           color=colors, alpha=0.6, edgecolor='white', linewidth=1.5)

    # Logo
    logo_img = get_logo(team_info['logo'])
    if logo_img:
        imagebox = OffsetImage(logo_img, zoom=0.5)
        ab = AnnotationBbox(imagebox, (0, 0), frameon=False)
        ax.add_artist(ab)

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color='white', size=12, fontweight='bold')
    ax.set_yticklabels([])
    ax.grid(color='grey', linestyle='--', alpha=0.3)

    st.pyplot(fig)

    # 7. Nøgletal i bunden
    st.write(f"### Nøgletal for {valgt_hold}")
    c1, c2, c3 = st.columns(3)
    c1.metric("xG pr. kamp", f"{target_team['XG_PG'].values[0]:.2f}")
    c2.metric("Pass %", f"{target_team['PASS_ACC'].values[0]:.1f}%")
    c3.metric("Felt-aktioner", f"{target_team['TOUCHBOX_PG'].values[0]:.1f}")

if __name__ == "__main__":
    vis_side()
