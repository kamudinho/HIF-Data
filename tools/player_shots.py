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

    # --- 1. DATA LOADING ---
    if "shotevents_data" not in st.session_state:
        with st.spinner("Henter skuddata..."):
            st.session_state["shotevents_data"] = load_snowflake_query(
                "shotevents", dp["comp_filter"], dp["season_filter"]
            )
        st.rerun()

    df_shots = st.session_state["shotevents_data"]
    df_spillere_hif = df_spillere if df_spillere is not None else dp.get("players")

    if df_shots is None or df_shots.empty or df_spillere_hif is None:
        st.warning("Kunne ikke indlæse data.")
        return

    # --- 2. FORBERED HVIDOVRE SPILLERLISTE (DIN CSV) ---
    s_df = df_spillere_hif.copy()
    s_df.columns = [str(c).upper().strip() for c in s_df.columns]

    def clean_id(val):
        if pd.isna(val): return "0"
        return str(val).split('.')[0].replace('.0', '').strip()

    # Opret PLAYER_ID_CLEAN på din Hvidovre-liste
    s_df['PLAYER_ID_CLEAN'] = s_df['PLAYER_WYID'].apply(clean_id)
    
    # Lav en liste over de PLAYER_IDs der må vises (dem fra din Hvidovre-CSV)
    tilladte_hif_ids = s_df['PLAYER_ID_CLEAN'].unique().tolist()
    
    # Lav navne-ordbog KUN for disse spillere
    navne_dict = dict(zip(s_df['PLAYER_ID_CLEAN'], s_df['SHORTNAME']))

    # --- 3. FILTRER SKUDDATA ---
    df_s = df_shots.copy()
    df_s['PLAYER_ID_CLEAN'] = df_s['PLAYER_WYID'].apply(clean_id)
    
    # KRITISK FILTRERING: Behold kun skud fra spillere, der findes i tilladte_hif_ids
    df_s = df_s[df_s['PLAYER_ID_CLEAN'].isin(tilladte_hif_ids)].copy()

    # Map navnene
    df_s['SPILLER_NAVN'] = df_s['PLAYER_ID_CLEAN'].map(navne_dict)

    if df_s.empty:
        st.warning("Ingen af spillerne fra din players.csv har registreret skud i Snowflake endnu.")
        return

    # --- 4. MÅL & xG LOGIK ---
    def to_bool(row):
        is_goal_flag = str(row.get('SHOTISGOAL')).lower() in ['true', '1', '1.0', 't', 'y', 'yes']
        is_goal_type = str(row.get('PRIMARYTYPE')).lower() in ['goal', 'penalty_goal']
        return is_goal_flag or is_goal_type

    df_s['IS_GOAL'] = df_s.apply(to_bool, axis=1)
    df_s['SHOTXG'] = pd.to_numeric(df_s['SHOTXG'], errors='coerce').fillna(0)

    # --- 5. UI LAYOUT ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller (Fra Hvidovre-trup)", options=spiller_liste)
        
        df_p = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
        df_p = df_p.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_p['NR'] = df_p.index + 1

        total_shots = len(df_p)
        total_goals = int(df_p['IS_GOAL'].sum())
        total_xg = df_p['SHOTXG'].sum()
        conv_rate = (total_goals / total_shots * 100) if total_shots > 0 else 0

        st.markdown(f"""
        <div style="border-left: 5px solid {TEAM_COLOR}; padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
            <h3 style="margin:0; color: {TEAM_COLOR};">{valgt_spiller}</h3>
            <hr>
            <small style="text-transform:uppercase; color:gray;">Afslutninger / Mål</small>
            <h2 style="margin:0;">{total_shots} / {total_goals}</h2>
            <br>
            <small style="text-transform:uppercase; color:gray;">Total xG</small>
            <h2 style="margin:0;">{total_xg:.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col_map:
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        for _, row in df_p.iterrows():
            is_goal = row['IS_GOAL']
            ptype = str(row.get('PRIMARYTYPE', 'shot')).lower()
            m_style = 'o' 
            if 'penalty' in ptype: m_style = 'P'
            elif 'free_kick' in ptype: m_style = 's'
        
            sc_size = (row['SHOTXG'] * 600) + 100
            if is_goal: sc_size += 150
            
            pitch.scatter(row['LOCATIONX'], row['LOCATIONY'], 
                          s=sc_size, edgecolors='white',
                          c='gold' if is_goal else TEAM_COLOR,
                          marker=m_style, ax=ax, zorder=3, alpha=0.8)
            
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['NR'])), 
                    color='black' if is_goal else 'white', 
                    ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
        
        st.pyplot(fig)
