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

HIF_RED = '#cc0000' 
HIF_BLUE = '#0055aa' 

def vis_side(df_spillere=None, hold_map=None):
     # --- TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">SCATTERPLOTS</h3>
        </div>
    """, unsafe_allow_html=True)
    
    dp = st.session_state.get("data_package")
    if not dp:
        st.error("Data pakke ikke fundet.")
        return

    # --- 1. HENT DATA FRA SNOWFLAKE ---
    # Vi bruger et unikt navn til cachen for denne side (shotevents_data)
    if "shotevents_data" not in st.session_state:
        with st.spinner("Henter skud fra Snowflake..."):
            c_f = dp.get("comp_filter")
            s_f = dp.get("season_filter")
            
            df_raw = load_snowflake_query("shotevents", c_f, s_f)
            
            # SIKKERHEDS-CHECK: Er data hentet og er de ikke tomme?
            if df_raw is not None and not df_raw.empty:
                df_raw.columns = [str(c).upper().strip() for c in df_raw.columns]
                
                # Tjek om kolonnen rent faktisk findes før vi renser den
                if 'PLAYER_WYID' in df_raw.columns:
                    df_raw['PLAYER_WYID'] = df_raw['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
                
                st.session_state["shotevents_data"] = df_raw
            else:
                # Gem en tom dataframe, så appen ikke prøver at hente igen og igen
                st.session_state["shotevents_data"] = pd.DataFrame()
        st.rerun()

    # Hent fra cache
    df_shots = st.session_state.get("shotevents_data", pd.DataFrame())
    df_csv_trup = df_spillere if df_spillere is not None else dp.get("players")

    # --- 2. STOP-KNAP (Hvis data mangler, stopper vi her uden fejl) ---
    if df_shots.empty:
        st.info("Ingen afslutninger fundet i databasen for den valgte periode.")
        return

    if 'PLAYER_WYID' not in df_shots.columns:
        st.error("Systemfejl: Kolonnen 'PLAYER_WYID' blev ikke fundet i data fra Snowflake.")
        return

    if df_shots is None or df_csv_trup is None:
        st.warning("Data mangler fra enten Snowflake eller din spillerliste.")
        return

    # --- 2. FORBERED DIN CSV-FILTER (Sandheden) ---
    df_csv = df_csv_trup.copy()
    df_csv.columns = [str(c).upper().strip() for c in df_csv.columns]
    df_csv['PLAYER_ID_CLEAN'] = df_csv['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Map ID -> Navn fra din CSV
    csv_navne_dict = dict(zip(df_csv['PLAYER_ID_CLEAN'], df_csv['NAVN']))

    # --- 3. FILTRER SNOWFLAKE DATA EFTER CSV ---
    # Vi bruger kun de skud, hvor spilleren findes i din CSV
    df_s = df_shots[df_shots['PLAYER_WYID'].isin(csv_navne_dict.keys())].copy()
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(csv_navne_dict)

    if df_s.empty:
        st.info("Ingen afslutninger fundet for spillere i din CSV.")
        return

    # --- 4. STATS LOGIK ---
    def to_bool(row):
        # Tjekker både SHOTISGOAL og om PRIMARYTYPE er goal
        is_goal_flag = str(row.get('SHOTISGOAL')).lower() in ['true', '1', '1.0', 't', 'y', 'yes']
        is_goal_type = str(row.get('PRIMARYTYPE')).lower() in ['goal', 'penalty_goal']
        return is_goal_flag or is_goal_type

    df_s['IS_GOAL'] = df_s.apply(to_bool, axis=1)
    df_s['SHOTXG'] = pd.to_numeric(df_s['SHOTXG'], errors='coerce').fillna(0)

    # --- 5. UI LAYOUT & VALG ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle spillere"] + spiller_liste)
        vis_type = st.radio("Vis afslutninger:", ["Alle", "Kun mål"], horizontal=True)
        
        if valgt_spiller == "Alle spillere":
            df_p = df_s.copy()
            overskrift = "Hele holdet"
        else:
            df_p = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
            overskrift = valgt_spiller

        if vis_type == "Kun mål":
            df_p = df_p[df_p['IS_GOAL'] == True].copy()

        df_p = df_p.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_p['NR'] = df_p.index + 1

        # Popover med tabel
        with st.popover("Oversigt over afslutninger", use_container_width=True):
            if not df_p.empty:
                vis_df = df_p[['NR', 'SPILLER_NAVN', 'MINUTE', 'SHOTXG', 'IS_GOAL']].copy()
                vis_df['RESULTAT'] = vis_df['IS_GOAL'].map({True: "MÅL", False: "SKUD"})
                st.dataframe(vis_df[['NR', 'SPILLER_NAVN', 'MINUTE', 'SHOTXG', 'RESULTAT']], hide_index=True)

        # Statistik Boks
        total_shots = len(df_p)
        total_goals = int(df_p['IS_GOAL'].sum())
        total_xg = df_p['SHOTXG'].sum()
        conv_rate = (total_goals / total_shots * 100) if total_shots > 0 else 0

        st.markdown(f"""
        <div style="border-left: 5px solid {HIF_RED}; padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
            <h3 style="margin:0;">{overskrift}</h3>
            <hr>
            <small>SKUD / MÅL</small>
            <h2 style="margin:0;">{total_shots} / {total_goals}</h2>
            <br>
            <small>KONVERTERINGSRATE</small>
            <h2 style="margin:0;">{conv_rate:.1f}%</h2>
            <br>
            <small>TOTAL xG</small>
            <h2 style="margin:0;">{total_xg:.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col_map:
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        if not df_p.empty:
            for _, row in df_p.iterrows():
                color = HIF_RED if row['IS_GOAL'] else HIF_BLUE
                sc_size = (row['SHOTXG'] * 600) + 100
                pitch.scatter(row['LOCATIONX'], row['LOCATIONY'], s=sc_size, c=color, 
                              edgecolors='white', ax=ax, zorder=3, alpha=0.8)
                ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['NR'])), 
                        color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
        st.pyplot(fig)
