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
    hold_navne = hold_data['TEAMNAME'].tolist()

    # --- CSS: FJERNER TOP PADDING I STREAMLIT ---
    st.markdown("""
        <style>
            .block-container { padding-top: 0rem !important; }
            [data-testid="stVerticalBlock"] > div:first-child { margin-top: 0px !important; }
        </style>
    """, unsafe_allow_html=True)

    menu_col, chart_col = st.columns([1, 8])

    with menu_col:
        st.write("### Vælg Hold")
        valgt_hold_navn = st.radio("Hold", hold_navne, label_visibility="collapsed", key="team_radio_select")
        st.session_state.selected_team = valgt_hold_navn

    with chart_col:
        target_team_raw = df[df['TEAMNAME'] == valgt_hold_navn]
        team_id = target_team_raw['TEAM_WYID'].values[0]
        logo_url = target_team_raw['IMAGEDATAURL'].values[0]

        # Data-beregning
        all_metrics_cols = [pair[1] for group in METRIC_PAIRS.values() for pair in group]
        for col in list(set(all_metrics_cols)):
            if col in df.columns and col != 'PPDA':
                df[col] = pd.to_numeric(df[col], errors='coerce') / df['MATCHES']
        
        target_team = df[df['TEAM_WYID'] == team_id]

        # --- 3. PIZZA CHART DESIGN (OPTIMERET TIL TOP) ---
        # Mindre højde på figuren fjerner tomrum
        fig, ax = plt.subplots(figsize=(10, 7.5), subplot_kw=dict(polar=True))
        fig.patch.set_alpha(0)
        ax.set_facecolor('none')
        
        # Aggressiv justering af margins - top=1.0 fjerner alt luft over diagrammet
        plt.subplots_adjust(left=0.05, right=0.95, top=1.0, bottom=0.0)
        
        V_OFFSET = 25
        LIMIT_Y = 120 # Stram grænse for at undgå tom yderring
        ax.set_ylim(0, LIMIT_Y)
        
        color_map = {'OFFENSIV': '#2ecc71', 'OPBYGNING': '#f1c40f', 'DEFENSIV': '#e74c3c'}
        plot_labels, values, display_values, plot_colors = [], [], [], []

        for group_name, pairs in METRIC_PAIRS.items():
            for display_label, data_col in pairs:
                if data_col not in df.columns: continue
                p_val = stats.percentileofscore(df[data_col].dropna(), target_team[data_col].values[0])
                if data_col in ['CONCEDEDGOALS', 'PPDA']: p_val = 100 - p_val
                
                plot_labels.append(display_label)
                scaled_val = V_OFFSET + (p_val * (80 - V_OFFSET) / 80)
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
            ax.add_artist(AnnotationBbox(OffsetImage(logo_img, zoom=0.5), (0, 0), frameon=False, zorder=10))

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.axis('off')

        # --- 4. TEKST OG LABELS (RYKKET TÆTTERE PÅ) ---
        for angle, label, disp, color in zip(angles, plot_labels, display_values, plot_colors):
            
            # Værdibokse (Farvede) - nu på Radius 110
            box_y = 110
            ax.text(angle, box_y, disp, ha='center', va='center', 
                    fontsize=9, fontweight='bold', color='white', zorder=12,
                    bbox=dict(facecolor=color, edgecolor='white', boxstyle='round,pad=0.3', linewidth=1))
            
            # Stat Labels (Hvide) - nu på Radius 142
            label_y = 142
            ax.text(angle, label_y, label, ha='center', va='center',
                    fontsize=7, fontweight='bold', color='black', zorder=11,
                    bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.4', linewidth=0.8))

        # Vis i appen uden ekstra margin
        st.pyplot(fig, use_container_width=True)

        # --- DOWNLOAD ---
        buf = BytesIO()
        fig.savefig(buf, format="png", transparent=True, bbox_inches='tight', dpi=300)
        st.download_button(
            label="Download Pizza Chart",
            data=buf.getvalue(),
            file_name=f"pizza_{valgt_hold_navn}.png",
            mime="image/png"
        )
