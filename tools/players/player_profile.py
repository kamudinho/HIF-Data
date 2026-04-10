import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO
from data.utils.mapping import get_action_label

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # 1. Team Mapping
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO")
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique() if mapping_lookup.get(str(u).lower().replace('t','')) is not None}

    col_spacer, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    # 2. Hent Data - Vi joiner på UUID og henter begge navne
    with st.spinner("Henter data..."):
        sql = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                e.PLAYER_OPTAUUID,
                COALESCE(p.MATCH_NAME, e.PLAYER_NAME) as VISNINGSNAVN, 
                e.MATCH_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            AND e.PLAYER_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all = conn.query(sql)
        
        if df_all is None or df_all.empty:
            st.warning("Ingen data fundet.")
            return

    # 3. Create Player Map (ID -> Navn) til selectbox
    # Vi laver en dictionary, så brugeren ser navnet, men vi får ID'et tilbage
    player_options = df_all[['PLAYER_OPTAUUID', 'VISNINGSNAVN']].drop_duplicates()
    player_dict = dict(zip(player_options['PLAYER_OPTAUUID'], player_options['VISNINGSNAVN']))
    
    t_col1, t_col2, _ = st.columns([1, 1, 1])
    # Selectbox returnerer nu PLAYER_OPTAUUID (key), men viser VISNINGSNAVN (value)
    valgt_player_id = t_col1.selectbox(
        "Vælg spiller", 
        options=list(player_dict.keys()), 
        format_func=lambda x: player_dict[x],
        label_visibility="collapsed"
    )
    
    visning = t_col2.selectbox("Visning", ["Heatmap", "Berøringer", "Afslutninger"], label_visibility="collapsed")

    # 4. FILTRER PÅ UUID (Dette er det vigtigste!)
    df_spiller = df_all[df_all['PLAYER_OPTAUUID'] == valgt_player_id].copy()
    df_spiller['qual_list'] = df_spiller['QUALIFIERS'].fillna('').str.split(',')
    df_spiller['Action_Label'] = df_spiller.apply(get_action_label, axis=1)

    # 5. Tegn profil
    kampe = df_spiller['MATCH_OPTAUUID'].nunique()
    p90 = 1 / kampe if kampe > 0 else 1

    c1, c2 = st.columns([1, 2.2])
    with c1:
        st.markdown(f"#### {player_dict[valgt_player_id]}")
        st.metric("Aktioner/90", round(len(df_spiller)*p90, 1))
        st.metric("Kampe", kampe)
        
        st.write("**Top Aktioner**")
        stats = df_spiller[df_spiller['Action_Label'] != 'Pasning'].groupby('Action_Label').size().sort_values(ascending=False).head(8)
        for akt, count in stats.items():
            st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:11px;'><span>{akt}</span><b>{count}</b></div>", unsafe_allow_html=True)

    with c2:
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        if visning == "Heatmap":
            pitch.kdeplot(df_spiller.EVENT_X, df_spiller.EVENT_Y, ax=ax, cmap='Blues', fill=True, levels=50, alpha=0.7)
        elif visning == "Berøringer":
            pitch.scatter(df_spiller.EVENT_X, df_spiller.EVENT_Y, ax=ax, color='#084594', s=50, edgecolors='white')
        
        st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
