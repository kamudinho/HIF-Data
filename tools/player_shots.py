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
    TEAM_WYID = 7470  # Hvidovre ID
    SEASONNAME = "2025/2026"

TEAM_COLOR = '#cc0000' # HIF Rød

def vis_side(df_spillere=None, hold_map=None):
    """
    Viser skudkort baseret på shotevents fra Snowflake.
    """
    st.markdown("<style>.main .block-container { padding-top: 1.5rem; }</style>", unsafe_allow_html=True)
    
    dp = st.session_state.get("data_package")
    if not dp:
        st.error("Data pakke ikke fundet.")
        return

    # --- 1. LAZY LOADING AF SKUDDATA ---
    if "shotevents_data" not in st.session_state:
        with st.spinner(f"Henter skuddata for {SEASONNAME}..."):
            st.session_state["shotevents_data"] = load_snowflake_query(
                "shotevents", dp["comp_filter"], dp["season_filter"]
            )
        st.rerun()

    df_shots = st.session_state["shotevents_data"]
    
    df_spillere = df_spillere if df_spillere is not None else dp.get("players")
    hold_map = hold_map if hold_map is not None else dp.get("hold_map", {})

    if df_shots is None or df_shots.empty:
        st.warning(f"Ingen skuddata fundet for {SEASONNAME}.")
        return

    # --- 2. DATA-RENS ---
    df_s = df_shots.copy()
    
    # Sikr numeriske værdier
    num_cols = ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE', 'TEAM_WYID']
    for col in num_cols:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce').fillna(0)

    # Robust mål-tjek (Inkluderer både flag og hændelsestype)
    def to_bool(row):
        is_goal_flag = str(row.get('SHOTISGOAL')).lower() in ['true', '1', '1.0', 't', 'y', 'yes']
        # Nogle gange gemmes straffe-mål i PRIMARYTYPE
        is_goal_type = str(row.get('PRIMARYTYPE')).lower() in ['goal', 'penalty_goal']
        return is_goal_flag or is_goal_type

    df_s['IS_GOAL'] = df_s.apply(to_bool, axis=1)
    
    # Filtrer på dit hold (Hvidovre)
    df_s = df_s[df_s['TEAM_WYID'] == int(TEAM_WYID)].copy()

    if df_s.empty:
        st.warning(f"Ingen skud registreret for hold ID {TEAM_WYID} i denne sæson.")
        return

    # --- 3. SPILLER MAPPING (FIX AF ID MATCH) ---
    s_df = df_spillere.copy()
    s_df.columns = [str(c).upper() for c in s_df.columns]

    # Funktion til at rense ID'er (fjerner .0 og mellemrum)
    def clean_id(val):
        if pd.isna(val): return "0"
        return str(val).split('.')[0].strip()

    s_df['PLAYER_ID_CLEAN'] = s_df['PLAYER_WYID'].apply(clean_id)
    
    if 'NAVN' not in s_df.columns:
        s_df['NAVN'] = s_df['SHORTNAME'].fillna(s_df['LASTNAME'])

    navne_dict = dict(zip(s_df['PLAYER_ID_CLEAN'], s_df['NAVN']))
    
    df_s['PLAYER_ID_CLEAN'] = df_s['PLAYER_WYID'].apply(clean_id)
    df_s['SPILLER_NAVN'] = df_s['PLAYER_ID_CLEAN'].map(navne_dict).fillna("Ukendt Spiller")

    # Debug info hvis der er ukendte spillere
    if "Ukendt Spiller" in df_s['SPILLER_NAVN'].values:
        missing = df_s[df_s['SPILLER_NAVN'] == "Ukendt Spiller"]['PLAYER_ID_CLEAN'].unique()
        st.caption(f"ℹ️ Info: Fandt ikke navne til ID: {', '.join(missing)} i players.csv")

    # --- 4. UI LAYOUT ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=spiller_liste)
        
        df_p = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
        df_p = df_p.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_p['NR'] = df_p.index + 1

        total_shots = len(df_p)
        total_goals = int(df_p['IS_GOAL'].sum())
        total_xg = df_p['SHOTXG'].sum()
        conv_rate = (total_goals / total_shots * 100) if total_shots > 0 else 0

        st.markdown(f"""
        <div style="border-left: 5px solid {TEAM_COLOR}; padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
            <small style="text-transform:uppercase; color:gray;">Afslutninger / Mål</small>
            <h2 style="margin:0;">{total_shots} / {total_goals}</h2>
            <hr style="margin:10px 0;">
            <small style="text-transform:uppercase; color:gray;">Total xG</small>
            <h2 style="margin:0;">{total_xg:.2f}</h2>
            <hr style="margin:10px 0;">
            <small style="text-transform:uppercase; color:gray;">Konvertering</small>
            <h2 style="margin:0;">{conv_rate:.1f}%</h2>
        </div>
        """, unsafe_allow_html=True)

        with st.popover("Se alle afslutninger", use_container_width=True):
            tabel_df = df_p.copy()
            tabel_df['RES'] = tabel_df['IS_GOAL'].map({True: "MÅL", False: "Afslutning"})
            st.dataframe(
                tabel_df[['NR', 'MINUTE', 'SHOTXG', 'RES']].rename(columns={'NR':'#','MINUTE':'Min','SHOTXG':'xG','RES':'Resultat'}),
                hide_index=True
            )

    with col_map:
        # Pitch setup
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        for _, row in df_p.iterrows():
            is_goal = row['IS_GOAL']
            ptype = str(row.get('PRIMARYTYPE', 'shot')).lower()
            
            # Form-logik
            m_style = 'o' 
            if 'penalty' in ptype: m_style = 'P'
            elif 'free_kick' in ptype: m_style = 's'
        
            # Placer punkt (Størrelse baseret på xG)
            # Vi bruger en minimum størrelse på 100, så selv lave xG skud kan ses
            sc_size = (row['SHOTXG'] * 600) + 100
            if is_goal: sc_size += 100 # Gør mål lidt tydeligere
            
            pitch.scatter(row['LOCATIONX'], row['LOCATIONY'], 
                          s=sc_size,
                          edgecolors='white',
                          c='gold' if is_goal else TEAM_COLOR,
                          marker=m_style, 
                          ax=ax,
                          zorder=3,
                          alpha=0.8)
            
            # Nummerering inde i markøren
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['NR'])), 
                    color='black' if is_goal else 'white', 
                    ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
        
        st.pyplot(fig)
