import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from PIL import Image
import requests
from io import BytesIO
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from data.data_load import _get_snowflake_conn

# --- 1. DATA OPSÆTNING ---
METRIC_PAIRS = {
    'OFFENSIV': [
        ('GOALS', 'GOALS'), ('SHOTS', 'SHOTS'), ('DRIBBLES', 'SUCCESSFULDRIBBLES'),
        ('ATTACKING ACTIONS', 'SUCCESSFULATTACKINGACTIONS'), ('TOUCH IN BOX', 'TOUCHINBOX'),
        ('CROSSES', 'SUCCESSFULCROSSES'), ('XGSHOT', 'XGSHOT')
    ],
    'OPBYGNING': [
        ('FORWARD PASSES', 'SUCCESSFULFORWARDPASSES'),
        ('PROGRESSIVE RUN', 'PROGRESSIVERUN'), ('PASSES', 'SUCCESSFULPASSES'),
        ('PASSES TO FINAL THIRD', 'SUCCESSFULPASSESTOFINALTHIRD')
    ],
    'DEFENSIV': [
        ('DEFENSIVEDUELS', 'DEFENSIVEDUELSWON'), ('AERIALDUELS', 'AERIALDUELSWON'),
        ('PPDA', 'PPDA'), ('INTERCEPTIONS', 'INTERCEPTIONS'),
        ('CONCEDEDGOALS', 'CONCEDEDGOALS'), ('RECOVERIES', 'RECOVERIES')
    ]
}

def get_logo(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None

def fetch_data():
    conn = _get_snowflake_conn()
    # Bruger dine saved values for 2025/2026 og NordicBet Liga (328)
    query = """
    SELECT 
        tm.TEAMNAME, tm.IMAGEDATAURL, t.TEAM_WYID, st.TOTALPLAYED AS MATCHES,
        t.GOALS, t.SHOTS, t.SUCCESSFULDRIBBLES, t.SUCCESSFULATTACKINGACTIONS, 
        t.TOUCHINBOX, t.SUCCESSFULCROSSES, t.XGSHOT, t.SUCCESSFULFORWARDPASSES, 
        t.PROGRESSIVERUN, t.SUCCESSFULPASSES, t.SUCCESSFULPASSESTOFINALTHIRD,
        t.DEFENSIVEDUELSWON, t.AERIALDUELSWON, t.PPDA, t.INTERCEPTIONS, 
        t.CONCEDEDGOALS, t.RECOVERIES
    FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL AS t
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS AS s ON t.SEASON_WYID = s.SEASON_WYID
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS AS tm ON t.TEAM_WYID = tm.TEAM_WYID
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS_STANDINGS AS st 
        ON t.TEAM_WYID = st.TEAM_WYID AND t.SEASON_WYID = st.SEASON_WYID
    WHERE t.COMPETITION_WYID = 328
    AND s.SEASONNAME = '2025/2026'
    """
    df = pd.DataFrame(conn.query(query))
    df.columns = [c.upper() for c in df.columns]
    return df

def vis_side(*args, **kwargs):
    if "df_pizza" not in st.session_state:
        st.session_state["df_pizza"] = fetch_data()
    
    df = st.session_state["df_pizza"].copy()
    hold_data = df[['TEAMNAME', 'IMAGEDATAURL', 'TEAM_WYID']].drop_duplicates().sort_values('TEAMNAME')
    
    if "selected_team" not in st.session_state:
        st.session_state.selected_team = hold_data.iloc[0]['TEAMNAME']

    # --- CSS: Sidebar-stil til venstre kolonne ---
    st.markdown("""
        <style>
            [data-testid="column"]:nth-child(1) {
                border-right: 1px solid #444;
                padding-right: 20px;
            }
            .logo-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                margin-bottom: 20px;
                cursor: pointer;
            }
            /* Gør knapperne diskrete */
            .stButton button {
                width: 100%;
                background-color: transparent;
                border: 1px solid #444;
                color: white;
            }
            .stButton button:hover {
                border-color: #FF4B4B;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- LAYOUT OPPDELING ---
    menu_col, chart_col = st.columns([1, 5])

    # --- 1. VENSTRE SIDE: LOGO MENU ---
    with menu_col:
        st.markdown("### Vælg Hold")
        for i, (_, row) in enumerate(hold_data.iterrows()):
            # Vis logo
            st.image(row['IMAGEDATAURL'], width=60)
            
            # Knap lige under logoet
            is_selected = st.session_state.selected_team == row['TEAMNAME']
            btn_label = f"✓ {row['TEAMNAME']}" if is_selected else row['TEAMNAME']
            
            if st.button(btn_label, key=f"btn_{row['TEAM_WYID']}", use_container_width=True):
                st.session_state.selected_team = row['TEAMNAME']
                st.rerun()
            st.markdown("---") # Lille adskiller

    # --- 2. HØJRE SIDE: DATA & CHART ---
    with chart_col:
        valgt_hold_navn = st.session_state.selected_team
        target_team_raw = df[df['TEAMNAME'] == valgt_hold_navn]
        team_id = target_team_raw['TEAM_WYID'].values[0]
        logo_url = target_team_raw['IMAGEDATAURL'].values[0]

        # Data-beregning (Normalisering)
        all_metrics_cols = [pair[1] for group in METRIC_PAIRS.values() for pair in group]
        for col in list(set(all_metrics_cols)):
            if col in df.columns and col != 'PPDA':
                df[col] = pd.to_numeric(df[col], errors='coerce') / df['MATCHES']
        
        target_team = df[df['TEAM_WYID'] == team_id]

        # --- 3. PIZZA CHART (Optimeret til højre side) ---
        fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(polar=True))
        fig.patch.set_alpha(0)
        ax.set_facecolor('none')
        
        # Vi giver den fuld gas på pladsen her
        plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        
        V_OFFSET = 28
        LIMIT_Y = 175 
        ax.set_ylim(0, LIMIT_Y)
        
        color_map = {'OFFENSIV': '#2ecc71', 'OPBYGNING': '#f1c40f', 'DEFENSIV': '#e74c3c'}
        plot_labels, values, display_values, plot_colors = [], [], [], []

        for group_name, pairs in METRIC_PAIRS.items():
            for display_label, data_col in pairs:
                if data_col not in df.columns: continue
                p_val = stats.percentileofscore(df[data_col].dropna(), target_team[data_col].values[0])
                if data_col in ['CONCEDEDGOALS', 'PPDA']: p_val = 100 - p_val
                
                plot_labels.append(display_label)
                scaled_val = V_OFFSET + (p_val * (100 - V_OFFSET) / 100)
                values.append(scaled_val)
                display_values.append(f"{target_team[data_col].values[0]:.1f}")
                plot_colors.append(color_map[group_name])

        num_vars = len(plot_labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)
        width = (2 * np.pi) / num_vars

        ax.bar(angles, [100] * num_vars, width=width, color='none', edgecolor='white', linewidth=0.6, alpha=0.3, zorder=1)
        ax.bar(angles, values, width=width, bottom=0, color=plot_colors, alpha=0.9, edgecolor='white', linewidth=1.2, zorder=3)

        logo_img = get_logo(logo_url)
        if logo_img:
            ax.add_artist(AnnotationBbox(OffsetImage(logo_img, zoom=0.8), (0, 0), frameon=False, zorder=10))

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.axis('off')

        # TEKST
        for angle, label, disp, color in zip(angles, plot_labels, display_values, plot_colors):
            angle_deg = np.rad2deg(angle)
            label_y = 160
            box_y = 136
            ha = 'center' if abs(angle_deg % 180) < 1 else ('left' if 0 < angle_deg < 180 else 'right')
            ax.text(angle, label_y, label, ha=ha, va='center', fontsize=10, fontweight='black', color='white')
            ax.text(angle, box_y, disp, ha='center', va='center', fontsize=11, fontweight='bold', color='white',
                    bbox=dict(facecolor=color, edgecolor='white', boxstyle='round,pad=0.4', linewidth=1))

        st.pyplot(fig, use_container_width=True)
