import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.utils.mapping import OPTA_QUALIFIERS, OPTA_EVENT_TYPES
import requests
from PIL import Image
from io import BytesIO

# --- 1. KONFIGURATION (Sikrer at disse er defineret) ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

# --- 2. HJÆLPEFUNKTIONER ---

@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    """Henter logo URL fra TEAMS mapping og returnerer et Image objekt."""
    # Finder URL baseret på UUID
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url:
        return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except:
        return None

def build_team_map(df_matches):
    """Mapper holdnavne til deres Opta UUIDs baseret på kørte kampe."""
    if df_matches.empty: return {}
    ids = pd.concat([df_matches['CONTESTANTHOME_OPTAUUID'], df_matches['CONTESTANTAWAY_OPTAUUID']]).unique()
    team_map = {}
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    for u_raw in ids:
        if pd.isna(u_raw): continue
        u_clean = str(u_raw).lower().strip().replace('t', '')
        matched_name = mapping_lookup.get(u_clean)
        if matched_name: 
            team_map[matched_name] = u_raw
    return team_map

def draw_logo_on_pitch(ax, logo_img):
    """Placerer logoet i øverste venstre hjørne af banen."""
    if logo_img:
        # [venstre, bund, bredde, højde] i relative akse-koordinater
        ax_logo = ax.inset_axes([0.02, 0.88, 0.10, 0.10], transform=ax.transAxes)
        ax_logo.imshow(logo_img)
        ax_logo.axis('off')

# --- 3. HOVEDFUNKTION ---

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Ingen forbindelse til Snowflake.")
        return

    # --- DATA LOADING (Nu med DB og LIGA_UUID defineret) ---
    with st.spinner("Henter data..."):
        # Hent generel kampinfo
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        # Hent mål-sekvenser
        sql_seq = f"""
            WITH GoalEvents AS (
                SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP, SEQUENCEID, EVENT_CONTESTANT_OPTAUUID
                FROM {DB}.OPTA_EVENTS WHERE EVENT_TYPEID = 16
                AND MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
            )
            SELECT e.*, ge.EVENT_CONTESTANT_OPTAUUID as GOAL_TEAM_ID, q.QUALIFIER_LIST
            FROM {DB}.OPTA_EVENTS e
            JOIN GoalEvents ge ON e.MATCH_OPTAUUID = ge.MATCH_OPTAUUID
            LEFT JOIN (
                SELECT EVENT_OPTAUUID, LISTAGG(QUALIFIER_QID, ',') AS QUALIFIER_LIST 
                FROM {DB}.OPTA_QUALIFIERS 
                GROUP BY 1
            ) q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_TIMESTAMP BETWEEN (ge.EVENT_TIMESTAMP - INTERVAL '20 seconds') AND ge.EVENT_TIMESTAMP
        """
        df_sequences = conn.query(sql_seq)

    if df_matches.empty:
        st.warning("Ingen kampe fundet i databasen.")
        return

    # --- UI LAYOUT ---
    team_map = build_team_map(df_matches)
    col_spacer, col_hold = st.columns([3, 1])
    with col_hold:
        valgte_navne = sorted(list(team_map.keys()))
        valgt_hold = st.selectbox("Vælg hold", valgte_navne, index=0, label_visibility="collapsed")
    
    valgt_uuid = team_map[valgt_hold]

    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "TOPSPILLERE"])

    with t2:
        if df_sequences.empty:
            st.info("Ingen sekvens-data fundet for denne liga.")
        else:
            team_seq = df_sequences[df_sequences['GOAL_TEAM_ID'] == valgt_uuid].copy()
            
            if team_seq.empty:
                st.info(f"Ingen scorede mål fundet for {valgt_hold}.")
            else:
                # Merge for at få modstander-detaljer
                team_seq = team_seq.merge(
                    df_matches[['MATCH_OPTAUUID', 'CONTESTANTHOME_NAME', 'CONTESTANTAWAY_NAME', 'CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']], 
                    on='MATCH_OPTAUUID', how='left'
                )

                goal_list = team_seq[team_seq['EVENT_TYPEID'] == 16].drop_duplicates('SEQUENCEID')
                
                goal_options = {}
                for idx, row in goal_list.iterrows():
                    is_h = row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
                    opp_name = row['CONTESTANTAWAY_NAME'] if is_h else row['CONTESTANTHOME_NAME']
                    opp_uuid = row['CONTESTANTAWAY_OPTAUUID'] if is_h else row['CONTESTANTHOME_OPTAUUID']
                    
                    goal_options[row['SEQUENCEID']] = {
                        'label': f"Mål vs. {opp_name} ({row['EVENT_TIMEMIN']}. min)",
                        'short': f"Mål vs. {opp_name}",
                        'opp_uuid': opp_uuid
                    }

                col_titel, col_velger = st.columns([2, 1])
                sel_id = col_velger.selectbox("Vælg scoring", list(goal_options.keys()), 
                                             format_func=lambda x: goal_options[x]['label'], label_visibility="collapsed")
                
                col_titel.markdown(f"### {goal_options[sel_id]['short']}")

                # Filter data for det valgte mål
                this_goal = team_seq[team_seq['SEQUENCEID'] == sel_id].sort_values('EVENT_TIMESTAMP')
                col_bane, col_tabel = st.columns([2, 1])

                with col_bane:
                    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey', goal_type='box')
                    fig, ax = pitch.draw(figsize=(10, 7))

                    # TEGN LOGO
                    opp_logo = get_logo_img(goal_options[sel_id]['opp_uuid'])
                    draw_logo_on_pitch(ax, opp_logo)

                    # Plot punkter og pile
                    for i in range(len(this_goal)):
                        row = this_goal.iloc[i]
                        is_g = int(row['EVENT_TYPEID']) == 16
                        
                        ax.scatter(row['EVENT_X'], row['EVENT_Y'], 
                                   color='#cc0000' if is_g else 'red', 
                                   s=180 if is_g else 70, 
                                   marker='s' if is_g else 'o', 
                                   edgecolors='black', zorder=10)
                        
                        ax.text(row['EVENT_X'], row['EVENT_Y'] + 2.5, row['PLAYER_NAME'], 
                                fontsize=8, ha='center', fontweight='bold',
                                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                        
                        if i < len(this_goal) - 1:
                            n_row = this_goal.iloc[i+1]
                            pitch.arrows(row['EVENT_X'], row['EVENT_Y'], n_row['EVENT_X'], n_row['EVENT_Y'], 
                                         width=1.5, color='grey', ax=ax, alpha=0.3)
                    
                    st.pyplot(fig)

                with col_tabel:
                    st.write("**Sekvens-detaljer:**")
                    # Vend tabellen så det seneste event (målet) står øverst
                    disp_df = this_goal[['PLAYER_NAME', 'EVENT_TYPEID']].iloc[::-1].copy()
                    disp_df.columns = ['Spiller', 'Aktion']
                    st.dataframe(disp_df, hide_index=True, use_container_width=True)
