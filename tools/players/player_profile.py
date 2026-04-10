import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
from data.utils.mapping import get_action_label

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # 1. Hent hold (standard mapping logik)
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO")
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique() if mapping_lookup.get(str(u).lower().replace('t','')) is not None}

    col_spacer, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    # 2. SQL - Vi bruger de præcise navne e.EVENT_X og e.EVENT_Y
    # Og vi trimmer UUIDs med det samme for at undgå match-fejl
    with st.spinner("Henter spillerprofil..."):
        sql = f"""
            SELECT 
                e.EVENT_X, 
                e.EVENT_Y, 
                e.EVENT_TYPEID, 
                UPPER(TRIM(e.PLAYER_OPTAUUID)) as PLAYER_ID,
                COALESCE(p.MATCH_NAME, e.PLAYER_NAME) as VISNINGSNAVN, 
                e.MATCH_OPTAUUID, 
                e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_PLAYERS p ON UPPER(TRIM(e.PLAYER_OPTAUUID)) = UPPER(TRIM(p.PLAYER_OPTAUUID))
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            AND e.PLAYER_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all = conn.query(sql)
        
        if df_all is None or df_all.empty:
            st.warning("Ingen data fundet for dette hold.")
            return

    # 3. Dropdown-logik baseret på UUID
    player_options = df_all[['PLAYER_ID', 'VISNINGSNAVN']].drop_duplicates().sort_values('VISNINGSNAVN')
    p_dict = dict(zip(player_options['PLAYER_ID'], player_options['VISNINGSNAVN']))
    
    t_col1, t_col2, _ = st.columns([1, 1, 1])
    valgt_pid = t_col1.selectbox("Spiller", options=list(p_dict.keys()), format_func=lambda x: p_dict[x], label_visibility="collapsed")
    visning = t_col2.selectbox("Type", ["Heatmap", "Berøringer", "Afslutninger"], label_visibility="collapsed")

    # 4. Filtrering og databehandling
    df_spiller = df_all[df_all['PLAYER_ID'] == valgt_pid].copy()
    df_spiller['qual_list'] = df_spiller['QUALIFIERS'].fillna('').str.split(',')
    df_spiller['Action_Label'] = df_spiller.apply(get_action_label, axis=1)

    # 5. Visualisering
    c1, c2 = st.columns([1, 2.5])
    
    with c1:
        st.subheader(p_dict[valgt_pid])
        kampe = df_spiller['MATCH_OPTAUUID'].nunique()
        st.metric("Kampe", kampe)
        st.metric("Total Aktioner", len(df_spiller))

    with c2:
        # pitch_type='opta' er afgørende her!
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        if not df_spiller.empty:
            # Sørg for at vi bruger EVENT_X og EVENT_Y som koordinater
            x = df_spiller['EVENT_X'].astype(float)
            y = df_spiller['EVENT_Y'].astype(float)
            
            if visning == "Heatmap":
                pitch.kdeplot(x, y, ax=ax, cmap='Blues', fill=True, levels=50, alpha=0.7)
            elif visning == "Berøringer":
                pitch.scatter(x, y, ax=ax, color='#084594', s=40, edgecolors='white', alpha=0.6)
            elif visning == "Afslutninger":
                skud = df_spiller[df_spiller['EVENT_TYPEID'].isin([13, 14, 15, 16])]
                pitch.scatter(skud['EVENT_X'], skud['EVENT_Y'], ax=ax, color='red', s=100, edgecolors='black')
        
        st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
