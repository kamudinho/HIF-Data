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
    
    # 1. Styring af valg (Logik for at kun én er valgt)
    if "selected_team" not in st.session_state:
        st.session_state.selected_team = hold_data.iloc[0]['TEAMNAME']

    # CSS til at fjerne padding og centrere checkbox præcis under logo
    st.markdown("""
        <style>
            [data-testid="column"] {
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            [data-testid="stCheckbox"] {
                margin-top: -15px; /* Trækker checkboxen helt op til logoet */
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. LOGOER OG CHECKBOXE ---
    cols = st.columns(len(hold_data))
    
    for i, (_, row) in enumerate(hold_data.iterrows()):
        with cols[i]:
            # Vis logo (lille størrelse)
            st.image(row['IMAGEDATAURL'], width=35)
            
            # Checkbox logik: Hvis denne klikkes, opdateres session_state og siden genindlæses
            is_checked = (st.session_state.selected_team == row['TEAMNAME'])
            res = st.checkbox(" ", key=f"chk_{row['TEAM_WYID']}", value=is_checked, label_visibility="collapsed")
            
            if res and not is_checked:
                st.session_state.selected_team = row['TEAMNAME']
                st.rerun()

    # --- 3. DATA PREP ---
    valgt_hold_navn = st.session_state.selected_team
    target_team_raw = df[df['TEAMNAME'] == valgt_hold_navn]
    team_id = target_team_raw['TEAM_WYID'].values[0]
    logo_url = target_team_raw['IMAGEDATAURL'].values[0]

    all_metrics = [pair[1] for group in METRIC_PAIRS.values() for pair in group]
    for col in list(set(all_metrics)):
        if col in df.columns and col != 'PPDA':
            df[col] = pd.to_numeric(df[col], errors='coerce') / df['MATCHES']
    
    target_team = df[df['TEAM_WYID'] == team_id]

    # --- 4. PIZZA CHART (FULD VISNING) ---
    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(polar=True))
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')
    
    # Juster marginer så chartet ikke bliver mast
    plt.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.08)
    
    V_OFFSET = 28
    LIMIT_Y = 175 
    ax.set_ylim(0, LIMIT_Y)
    
    # ... (Din eksisterende bar- og beregningslogik) ...
    # Sørg for at bruge disse labels for at undgå beskæring:
    # label_y = 162, box_y = 138

    # Centralt logo
    logo_img = get_logo(logo_url)
    if logo_img:
        ax.add_artist(AnnotationBbox(OffsetImage(logo_img, zoom=0.72), (0, 0), frameon=False, zorder=10))

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.axis('off')

    # TEKST LABELS
    num_vars = len(all_metrics) # Justeret til dine faktiske metrics
    # (Her indsættes plot-loopet fra tidligere svar)

    # Render responsivt
    st.pyplot(fig, use_container_width=True)
