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
    
    # Her bruger vi dine faste værdier: 
    # Sæson 25/26 = 188330, NordicBet Liga = 328
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
    
    # Snowflake returnerer UPPERCASE - vi tvinger dem til små bogstaver
    df.columns = [c.lower() for c in df.columns]
    
    # VIGTIGT: Sørg for at team_wyid er et heltal (int) for præcis matching
    if not df.empty:
        df['team_wyid'] = df['team_wyid'].astype(int)
        
    return df

def vis_side(*args, **kwargs):
    # Overskrift tilpasset din app
    st.title("📊 Hvidovre App: Performance Profiler (1. Div)")

    if "team_stats_1div" not in st.session_state:
        with st.spinner("Henter data for NordicBet Liga..."):
            st.session_state["team_stats_1div"] = fetch_team_data()
    
    df = st.session_state["team_stats_1div"].copy()

    if df.empty:
        st.error("Kunne ikke finde data for COMPETITION_WYID 328 i Snowflake.")
        return

    # 1. Valg af hold - vi filtrerer TEAMS mappingen
    hold_1div = [navn for navn, info in TEAMS.items() if info.get("league") == "1. Division"]
    valgt_hold = st.selectbox("Vælg hold til analyse:", sorted(hold_1div))
    
    team_info = TEAMS[valgt_hold]
    # Her henter vi holdets ID fra din mapping og sikrer os det er en INT
    team_wyid = int(team_info['team_wyid'])

    # 2. Beregninger
    df['goals_pg'] = df['goals'] / df['matches']
    df['xg_pg'] = df['xgshot'] / df['matches']
    df['shots_pg'] = df['shots'] / df['matches']
    df['passes_pg'] = df['passes'] / df['matches']
    df['pass_acc'] = (df['successfulpasses'] / df['passes']) * 100
    df['def_duels_pg'] = df['defensiveduels'] / df['matches']
    df['intercept_pg'] = df['interceptions'] / df['matches']
    df['touchbox_pg'] = df['touchinbox'] / df['matches']

    # 3. Find det valgte hold (Nu matcher de på tværs af INT typer)
    target_team = df[df['team_wyid'] == team_wyid]

    if target_team.empty:
        st.warning(f"Ingen data fundet for {valgt_hold} (ID: {team_wyid}). Tjek om ID'et findes i Snowflake.")
        # Debug hjælp:
        # st.write("Tilgængelige ID'er i DF:", df['team_wyid'].unique())
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
        # Beregn percentil
        p_val = stats.percentileofscore(df[col].dropna(), target_team[col].values[0])
        labels.append(label)
        values.append(p_val)
        colors.append(color)

    # 5. Plotting
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')
    
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    
    # Pizza slices
    ax.bar(angles, values, width=0.7, color=colors, alpha=0.6, edgecolor='white', linewidth=1)

    # Logo midt i
    logo = get_logo(team_info['logo'])
    if logo:
        imagebox = OffsetImage(logo, zoom=0.4)
        ab = AnnotationBbox(imagebox, (0, 0), frameon=False)
        ax.add_artist(ab)

    # Styling
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color='white', size=11, fontweight='bold')
    ax.set_yticklabels([])
    ax.grid(color='grey', linestyle='--', alpha=0.3)
    
    st.pyplot(fig)

    # 6. Oversigtstabel
    st.write(f"### Stats pr. kamp for {valgt_hold}")
    st.dataframe(target_team[['matches', 'goals_pg', 'xg_pg', 'pass_acc', 'touchbox_pg']].style.format(precision=2))
