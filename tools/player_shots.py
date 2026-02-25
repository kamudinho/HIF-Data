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
        # Hent unikke navne og tilføj "Alle spillere" øverst
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

        # Metrics boks
        total_shots = len(df_p)
        total_goals = int(df_p['IS_GOAL'].sum())
        total_xg = df_p['SHOTXG'].sum()

        st.markdown(f"""
        <div style="border-left: 5px solid {TEAM_COLOR}; padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
            <h3 style="margin:0;">{overskrift}</h3>
            <hr>
            <small>AFSLUTNINGER / MÅL</small>
            <h2 style="margin:0;">{total_shots} / {total_goals}</h2>
            <br>
            <small>TOTAL xG</small>
            <h2 style="margin:0;">{total_xg:.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

        # --- NY POPOVER MED DETALJER ---
        st.write("") # Margin
        with st.popover("Se detaljeret skudliste", use_container_width=True):
            if not df_p.empty:
                # Forbered tabel-data
                tabel_df = df_p[['NR', 'MINUTE', 'SHOTXG', 'IS_GOAL', 'SPILLER_NAVN']].copy()
                tabel_df['RESULTAT'] = tabel_df['IS_GOAL'].map({True: "MÅL", False: "Afslutning"})
                
                # Omdøb for pæn visning
                vis_df = tabel_df[['NR', 'SPILLER_NAVN', 'MINUTE', 'SHOTXG', 'RESULTAT']].rename(columns={
                    'NR': '#',
                    'SPILLER_NAVN': 'Spiller',
                    'MINUTE': 'Min',
                    'SHOTXG': 'xG',
                    'RESULTAT': 'Udfald'
                })
                
                st.dataframe(vis_df, hide_index=True, use_container_width=True)
            else:
                st.write("Ingen data at vise.")

    with col_map:
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        # Tegn skud
        if not df_p.empty:
            for _, row in df_p.iterrows():
                is_goal = row['IS_GOAL']
                ptype = str(row.get('PRIMARYTYPE', 'shot')).lower()
                
                # Form skift
                m_style = 'o' 
                if 'penalty' in ptype: m_style = 'P'
                elif 'free_kick' in ptype: m_style = 's'
            
                # Skalering af størrelse (xG styret)
                sc_size = (row['SHOTXG'] * 600) + 100
                
                pitch.scatter(row['LOCATIONX'], row['LOCATIONY'], 
                              s=sc_size, edgecolors='white',
                              c='gold' if is_goal else TEAM_COLOR,
                              marker=m_style, ax=ax, zorder=3, alpha=0.8)
                
                # Nummerering på banen
                ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['NR'])), 
                        color='black' if is_goal else 'white', 
                        ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
        
        st.pyplot(fig)
