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

# --- 1. DIT DESIGN OPSÆTNING ---
METRIC_PAIRS = {
    'OFFENSIV': [
        ('GOALS', 'GOALS'), ('SHOTS', 'SHOTS'), ('XGSHOT', 'XGSHOT')
    ],
    'OPBYGNING': [
        ('FORWARD PASSES', 'FORWARDPASSES'),
        ('PASSES TO FINAL THIRD', 'PASSESTOFINALTHIRD')
    ],
    'DEFENSIV': [
        ('PPDA', 'PPDA'), ('CONCEDED GOALS', 'CONCEDEDGOALS')
    ]
}

def get_logo(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None

def fetch_team_data():
    conn = _get_snowflake_conn()
    # Din præcise query fra tidligere
    query = """
    SELECT DISTINCT 
        tm.TEAMNAME, t.GOALS, t.XGSHOT, t.CONCEDEDGOALS, t.SHOTS, t.PPDA,
        t.PASSESTOFINALTHIRD, t.FORWARDPASSES, st.TOTALPLAYED AS MATCHES, t.TEAM_WYID
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
        df.columns = [c.upper() for c in df.columns] # Vi bruger UPPER her pga. dit design
    return df

def vis_side(*args, **kwargs):
    st.title("📊 Hvidovre IF: Modstander Analyse")

    if "team_data_NB" not in st.session_state:
        st.session_state["team_data_NB"] = fetch_team_data()
    
    df = st.session_state["team_data_NB"].copy()

    if df.empty:
        st.error("Kunne ikke hente data fra Snowflake.")
        return

    # 1. Valg af hold (Hvidovre-app stil)
    hold_navne = sorted(df['TEAMNAME'].unique())
    valgt_hold = st.selectbox("Vælg hold til analyse:", hold_navne)
    target_team = df[df['TEAMNAME'] == valgt_hold]

    # 2. Normalisering (Stats pr. kamp)
    for group in METRIC_PAIRS.values():
        for label, col in group:
            if col in df.columns and col not in ['PPDA', 'MATCHES']:
                df[col] = df[col] / df['MATCHES']

    # 3. Pizza Chart Logik (Dit design)
    plot_labels, values, display_values, plot_colors = [], [], [], []
    color_map = {'OFFENSIV': '#2ecc71', 'OPBYGNING': '#f1c40f', 'DEFENSIV': '#e74c3c'}

    for group_name, pairs in METRIC_PAIRS.items():
        for label, col in pairs:
            p_val = stats.percentileofscore(df[col].dropna(), target_team[col].values[0])
            if col in ['CONCEDEDGOALS', 'PPDA']: p_val = 100 - p_val
            
            plot_labels.append(label)
            values.append(p_val)
            display_values.append(f"{target_team[col].values[0]:.1f}")
            plot_colors.append(color_map[group_name])

    # 4. PLOTTING (Gennemsigtig + Hvid tekst)
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    fig.patch.set_alpha(0) # Gennemsigtig baggrund
    ax.set_facecolor('none')
    
    num_vars = len(plot_labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)
    width = (2 * np.pi) / num_vars

    # Selve pizza-skiverne
    ax.bar(angles, values, width=width, bottom=20, color=plot_colors, 
           alpha=0.9, edgecolor='white', linewidth=1.5, align='edge')

    # Logo midt i
    # Vi prøver at finde logoet via TEAMS mapping eller Snowflake URL
    logo_url = target_team['IMAGEDATAURL'].values[0] if 'IMAGEDATAURL' in target_team else None
    if logo_url:
        logo_img = get_logo(logo_url)
        if logo_img:
            ax.add_artist(AnnotationBbox(OffsetImage(logo_img, zoom=0.6), (0, 0), frameon=False))

    # Styling (Hvid tekst)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.axis('off')

    for angle, label, disp, color in zip(angles, plot_labels, display_values, plot_colors):
        text_angle = angle + (width / 2)
        ax.text(text_angle, 125, label, ha='center', color='white', fontweight='bold', fontsize=10)
        ax.text(text_angle, 110, disp, ha='center', color='white', fontweight='bold',
                bbox=dict(facecolor=color, edgecolor='white', boxstyle='round,pad=0.3'))

    st.pyplot(fig)
