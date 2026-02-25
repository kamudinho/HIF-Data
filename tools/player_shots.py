import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from data.data_load import load_snowflake_query

# --- 0. KONFIGURATION ---
try:
    from data.season_show import TEAM_WYID, SEASONNAME
except ImportError:
    TEAM_WYID = 7490  
    SEASONNAME = "2025/2026"

TEAM_COLOR = '#cc0000' # HIF Rød

def vis_side(df_spillere=None, hold_map=None):
    st.markdown("<style>.main .block-container { padding-top: 1.5rem; }</style>", unsafe_allow_html=True)
    
    dp = st.session_state.get("data_package")
    if not dp:
        st.error("Data pakke ikke fundet.")
        return

    # --- 1. HENT DATA ---
    if "shotevents_data" not in st.session_state:
        with st.spinner("Henter skud..."):
            st.session_state["shotevents_data"] = load_snowflake_query(
                "shotevents", dp["comp_filter"], dp["season_filter"]
            )
        st.rerun()

    df_shots = st.session_state["shotevents_data"]
    df_trup = df_spillere if df_spillere is not None else dp.get("players")

    if df_shots is None or df_trup is None:
        st.warning("Data mangler.")
        return

    # --- 2. BEHANDL DIN CSV (Sandheden) ---
    s_df = df_trup.copy()
    # Rens kolonnenavne (fjerner whitespace og gør dem store)
    s_df.columns = [str(c).upper().strip() for c in s_df.columns]

    def clean_id(val):
        if pd.isna(val): return "0"
        return str(val).split('.')[0].replace('.0', '').strip()

    # Opret renset ID kolonne fra din CSV
    s_df['PLAYER_ID_CLEAN'] = s_df['PLAYER_WYID'].apply(clean_id)
    
    # Lav ordbog KUN med PLAYER_WYID og NAVN fra din fil
    # Hvis et ID findes flere gange, tager den den sidste
    navne_dict = dict(zip(s_df['PLAYER_ID_CLEAN'], s_df['NAVN']))

    # --- 3. FILTRER SNOWFLAKE DATA ---
    df_s = df_shots.copy()
    df_s['PLAYER_ID_CLEAN'] = df_s['PLAYER_WYID'].apply(clean_id)
    
    # TEST-LOGIK: Vi beholder KUN skud, hvor ID findes i din players.csv
    df_s = df_s[df_s['PLAYER_ID_CLEAN'].isin(navne_dict.keys())].copy()
    
    # Map NAVN fra din csv over på skuddata
    df_s['SPILLER_NAVN'] = df_s['PLAYER_ID_CLEAN'].map(navne_dict)

    if df_s.empty:
        st.info("Ingen match fundet mellem Snowflake-skud og de ID'er, du har i din players.csv.")
        return

    # --- 4. STATS LOGIK ---
    def to_bool(row):
        is_goal_flag = str(row.get('SHOTISGOAL')).lower() in ['true', '1', '1.0', 't', 'y', 'yes']
        is_goal_type = str(row.get('PRIMARYTYPE')).lower() in ['goal', 'penalty_goal']
        return is_goal_flag or is_goal_type

    df_s['IS_GOAL'] = df_s.apply(to_bool, axis=1)
    df_s['SHOTXG'] = pd.to_numeric(df_s['SHOTXG'], errors='coerce').fillna(0)

    # --- 5. UI LAYOUT & VALG ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        # 1. Dropdown
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgmuligheder = ["Alle spillere"] + spiller_liste
        valgt_spiller = st.selectbox("Vælg spiller (Fra din CSV)", options=valgmuligheder)
        
        # Filtrering baseret på valg
        if valgt_spiller == "Alle spillere":
            df_p = df_s.copy()
            overskrift = "Hele holdet"
        else:
            df_p = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
            overskrift = valgt_spiller

        df_p = df_p.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_p['NR'] = df_p.index + 1

        # 2. Popover - HER VAR FEJLEN (Indrykning rettet)
        with st.popover("Oversigt over afslutninger", use_container_width=True):
            if not df_p.empty:
                tabel_df = df_p[['NR', 'SPILLER_NAVN', 'MINUTE', 'SHOTXG', 'IS_GOAL']].copy()
                tabel_df['RESULTAT'] = tabel_df['IS_GOAL'].map({True: "MÅL", False: "Afslutning"})
                
                vis_df = tabel_df[['NR', 'SPILLER_NAVN', 'MINUTE', 'SHOTXG', 'RESULTAT']].rename(columns={
                    'NR': '#', 'SPILLER_NAVN': 'Spiller', 'MINUTE': 'Min', 'SHOTXG': 'xG', 'RESULTAT': 'Udfald'
                })
                
                st.dataframe(
                    vis_df, 
                    hide_index=True, 
                    use_container_width=True, 
                    height=min(len(vis_df) * 35 + 38, 500),
                    column_config={
                        "#": st.column_config.Column(width="small", help="Nummer på banen"),
                        "Spiller": st.column_config.Column(width="medium"),
                        "Min": st.column_config.Column(width="small"),
                        "xG": st.column_config.NumberColumn(width="small", format="%.2f"),
                        "Udfald": st.column_config.Column(width="medium")
                    }
                )
            else:
                st.write("Ingen data fundet.")

        # 3. Statistik Boks
        total_shots = len(df_p)
        total_goals = int(df_p['IS_GOAL'].sum())
        total_xg = df_p['SHOTXG'].sum()
        conv_rate = (total_goals / total_shots * 100) if total_shots > 0 else 0

        st.markdown(f"""
        <div style="border-left: 5px solid {TEAM_COLOR}; padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
            <h3 style="margin:0; color: #333;">{overskrift}</h3>
            <hr style="margin: 10px 0;">
            <small style="color:gray; text-transform:uppercase;">Afslutninger / Mål</small>
            <h2 style="margin:0;">{total_shots} / {total_goals}</h2>
            <div style="margin: 10px 0;"></div>
            <small style="color:gray; text-transform:uppercase;">Konvertering</small>
            <h2 style="margin:0;">{conv_rate:.1f}%</h2>
            <div style="margin: 10px 0;"></div>
            <small style="color:gray; text-transform:uppercase;">Total xG</small>
            <h2 style="margin:0;">{total_xg:.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
