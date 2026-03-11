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
    
    # Vi bruger en JOIN for at sikre, at vi rammer de rigtige navne i Snowflake
    # Dette eliminerer fejlen med SEASON_WYID mismatch
    query = """
    SELECT 
        t.TEAM_WYID, t.MATCHES, t.GOALS, t.SHOTS, t.XGSHOT, 
        t.PASSES, t.SUCCESSFULPASSES, t.DEFENSIVEDUELS, 
        t.INTERCEPTIONS, t.TOUCHINBOX
    FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL t
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_COMPETITIONS c ON t.COMPETITION_WYID = c.COMPETITION_WYID
    WHERE c.COMPETITIONNAME = 'NordicBet Liga' 
    AND s.SEASONNAME = '2025/2026'
    """
    df_res = conn.query(query)
    df = pd.DataFrame(df_res)
    
    if df.empty:
        return df

    # Tving kolonner til små bogstaver
    df.columns = [c.lower() for c in df.columns]
    
    # Sikr at ID er heltal for korrekt matching med TEAMS mapping
    df['team_wyid'] = pd.to_numeric(df['team_wyid']).astype(int)
    return df

def vis_side(*args, **kwargs):
    # Direkte til titlen som ønsket
    st.title("📊 Hvidovre App: Performance Profiler")

    # Session State håndtering for hurtigere indlæsning
    if "team_stats_1div" not in st.session_state:
        with st.spinner("Henter data fra Snowflake..."):
            st.session_state["team_stats_1div"] = fetch_team_data()
    
    df = st.session_state["team_stats_1div"].copy()

    # Hvis data stadig er tom, vis fejl og genindlæs-knap
    if df.empty:
        st.error("Fejl: Ingen rækker fundet for NordicBet Liga 2025/2026 i Snowflake.")
        if st.button("Tving genindlæsning af data"):
            st.session_state.pop("team_stats_1div")
            st.rerun()
        return

    # 1. Valg af hold
    hold_1div = [navn for navn, info in TEAMS.items() if info.get("league") == "1. Division"]
    valgt_hold = st.selectbox("Vælg hold:", sorted(hold_1div))
    
    team_info = TEAMS[valgt_hold]
    team_wyid = int(team_info['team_wyid'])

    # 2. Beregninger (PG = Per Game)
    # Vi bruger en kopi for at undgå SettingWithCopyWarning
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
        st.warning(f"Holdet '{valgt_hold}' (ID: {team_wyid}) blev ikke fundet i liga-dataen.")
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
        # Beregn percentil score i forhold til resten af ligaen
        p_val = stats.percentileofscore(df[col], target_team[col].values[0])
        labels.append(label)
        values.append(p_val)
        colors.append(color)

    # 5. Plotting (Pizza Chart)
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')
    
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    
    # Sørg for at lukke cirklen ved at gentage første element (valgfrit for bar charts)
    ax.bar(angles, values, width=0.7, color=colors, alpha=0.6, edgecolor='white', linewidth=1)

    # Tilføj logo i midten
    logo = get_logo(team_info['logo'])
    if logo:
        imagebox = OffsetImage(logo, zoom=0.4)
        ab = AnnotationBbox(imagebox, (0, 0), frameon=False)
        ax.add_artist(ab)

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color='white', size=11, fontweight='bold')
    ax.set_yticklabels([]) # Skjul 0-100 skalaen
    ax.grid(color='grey', linestyle='--', alpha=0.3)
    
    st.pyplot(fig)

    # 6. Tabelvisning (Bunden)
    st.dataframe(
        target_team[['matches', 'goals_pg', 'xg_pg', 'pass_acc', 'touchbox_pg']].style.format(precision=2),
        use_container_width=True
    )

if __name__ == "__main__":
    vis_side()
