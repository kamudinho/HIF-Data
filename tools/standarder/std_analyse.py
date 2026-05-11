import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_setpiece_data_v2():
    conn = _get_snowflake_conn()
    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    
    # Rettet SQL: Vi bruger EVENT_OPTAID (Optas sekventielle ID) til at finde næste hændelse
    sql = f"""
        WITH END_COORDS AS (
            SELECT EVENT_OPTAUUID, 
                   MAX(CASE WHEN QUALIFIER_QID = 140 THEN QUALIFIER_VALUE END) as ENDX,
                   MAX(CASE WHEN QUALIFIER_QID = 141 THEN QUALIFIER_VALUE END) as ENDY
            FROM {DB}.OPTA_QUALIFIERS WHERE QUALIFIER_QID IN (140, 141) GROUP BY 1
        ),
        SHOTS AS (
            SELECT MATCH_OPTAUUID, EVENT_OPTAID 
            FROM {DB}.OPTA_EVENTS WHERE EVENT_TYPEID IN (13, 14, 15, 16)
        )
        SELECT 
            e.EVENT_OPTAUUID, e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.EVENT_OPTAID,
            e.EVENT_CONTESTANT_OPTAUUID, e.MATCH_OPTAUUID,
            ec.ENDX, ec.ENDY, q.QUALIFIER_QID,
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME,
            CASE WHEN s.EVENT_OPTAID IS NOT NULL THEN 1 ELSE 0 END as LEADS_TO_SHOT
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN END_COORDS ec ON e.EVENT_OPTAUUID = ec.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        -- Vi joiner på den næste hændelse (ID + 1) i samme kamp
        LEFT JOIN SHOTS s ON e.MATCH_OPTAUUID = s.MATCH_OPTAUUID AND s.EVENT_OPTAID = e.EVENT_OPTAID + 1
        WHERE q.QUALIFIER_QID IN (2, 5, 107, 124)
        AND e.MATCH_OPTAUUID IN ({match_sql})
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    
    # Konverter til numerisk for beregninger
    for col in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    type_map = {2: "Hjørnespark", 124: "Hjørnespark", 5: "Frispark", 107: "Indkast"}
    df['SET_PIECE_TYPE'] = df['QUALIFIER_QID'].map(type_map)
    return df

def to_metric(val, total_m): return val * (total_m / 100)

def vis_side():
    df_all = load_setpiece_data_v2()
    if df_all.empty: return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    
    # --- FILTRE I SIDEBAR/TOP ---
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: t_sel = st.selectbox("Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()
    
    with c2: sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with c3: 
        p_list = ["Alle spillere"] + sorted(df_team[df_team['SET_PIECE_TYPE']==sp_type]['PLAYER_NAME'].unique().tolist())
        p_sel = st.selectbox("Spiller", p_list)
    with c4: outcome_sel = st.selectbox("Resultat", ["Alle", "Kun ført til afslutning"])

    # --- DATAFILTRERING ---
    mask = (df_team['SET_PIECE_TYPE'] == sp_type)
    if p_sel != "Alle spillere": mask &= (df_team['PLAYER_NAME'] == p_sel)
    if outcome_sel == "Kun ført til afslutning": mask &= (df_team['LEADS_TO_SHOT'] == 1)
    
    df_plot = df_team[mask].copy()
    
    # Skalering
    df_plot['X_M'] = df_plot['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_plot['Y_M'] = df_plot['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_plot['ENDX_M'] = df_plot['ENDX'].apply(lambda x: to_metric(x, 105))
    df_plot['ENDY_M'] = df_plot['ENDY'].apply(lambda y: to_metric(y, 68))

    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', '#cc0000')

    # --- VISUALISERING ---
    col_p, col_s = st.columns([2, 1])

    with col_p:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(55, 105)

        # 1. Tegn "Zoner" (Hexbin eller heatmap-agtige felter for landinger)
        if not df_plot.dropna(subset=['ENDX_M', 'ENDY_M']).empty:
            # Vi bruger hexbin til at vise densitet af landinger
            pitch.hexbin(df_plot.ENDX_M, df_plot.ENDY_M, ax=ax, gridsize=(10, 10), cmap='Reds', alpha=0.5, edgecolors='#f0f0f0')
            
            # 2. Tegn pile ovenpå, men meget subtilt (kun hvis der ikke er for mange)
            alpha_val = 0.4 if len(df_plot) < 50 else 0.1
            pitch.arrows(df_plot.X_M, df_plot.Y_M, df_plot.ENDX_M, df_plot.ENDY_M, 
                         width=1, headwidth=3, color=t_color, ax=ax, alpha=alpha_val)

        st.pyplot(fig)

    with col_s:
        st.metric("Antal aktioner", len(df_plot))
        if outcome_sel == "Alle" and len(df_plot) > 0:
            shots_count = df_plot['LEADS_TO_SHOT'].sum()
            st.metric("Heraf afslutninger", int(shots_count), f"{shots_count/len(df_plot)*100:.1f}%")
        
        st.write("**Top eksekutører i udvalg:**")
        st.dataframe(df_plot['PLAYER_NAME'].value_counts(), use_container_width=True)

if __name__ == "__main__":
    vis_side()
