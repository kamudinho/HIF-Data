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
HIF_BLUE = '#0055aa' # HIF Blå farve

def vis_side(df_spillere=None, hold_map=None):
    st.markdown("<style>.main .block-container { padding-top: 1.5rem; }</style>", unsafe_allow_html=True)
    
    dp = st.session_state.get("data_package")
    if not dp:
        st.error("Data pakke ikke fundet.")
        return

    # --- 1. HENT DATA ---
    if "shotevents_data" not in st.session_state:
        with st.spinner("Henter skud..."):
            # Vi henter værdierne fra din data_package (dp) ved at bruge de korrekte navne
            # Vi bruger .get() med en fallback til dine standardværdier
            comp_id = dp.get("COMPETITION_WYID", 328)
            season_id = dp.get("SEASONNAME", "2025/2026")
            
            # Nu kalder vi Snowflake med de rigtige variable
            st.session_state["shotevents_data"] = load_snowflake_query(
                "shotevents", comp_id, season_id
            )
        st.rerun()

    df_shots = st.session_state["shotevents_data"]
    df_trup = df_spillere if df_spillere is not None else dp.get("players")

    if df_shots is None or df_trup is None:
        st.warning("Data mangler.")
        return

    # --- 2. BEHANDL DIN CSV (Sandheden) ---
    s_df = df_trup.copy()
    s_df.columns = [str(c).upper().strip() for c in s_df.columns]

    def clean_id(val):
        if pd.isna(val): return "0"
        return str(val).split('.')[0].replace('.0', '').strip()

    s_df['PLAYER_ID_CLEAN'] = s_df['PLAYER_WYID'].apply(clean_id)
    navne_dict = dict(zip(s_df['PLAYER_ID_CLEAN'], s_df['NAVN']))

    # --- 3. FILTRER SNOWFLAKE DATA ---
    df_s = df_shots.copy()
    df_s['PLAYER_ID_CLEAN'] = df_s['PLAYER_WYID'].apply(clean_id)
    df_s = df_s[df_s['PLAYER_ID_CLEAN'].isin(navne_dict.keys())].copy()
    df_s['SPILLER_NAVN'] = df_s['PLAYER_ID_CLEAN'].map(navne_dict)

    if df_s.empty:
        st.info("Ingen match fundet.")
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
        # 1. Filtre
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgmuligheder = ["Alle spillere"] + spiller_liste
        valgt_spiller = st.selectbox("Vælg spiller", options=valgmuligheder)
        
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

        # 2. Popover
        with st.popover("Oversigt over afslutninger", use_container_width=True):
            if not df_p.empty:
                tabel_df = df_p[['NR', 'SPILLER_NAVN', 'MINUTE', 'SHOTXG', 'IS_GOAL']].copy()
                tabel_df['RESULTAT'] = tabel_df['IS_GOAL'].map({True: "MÅL", False: "SKUD"})
                
                vis_df = tabel_df[['NR', 'SPILLER_NAVN', 'MINUTE', 'SHOTXG', 'RESULTAT']].rename(columns={
                    'NR': '#', 'SPILLER_NAVN': 'SPILLER', 'MINUTE': 'MIN', 'SHOTXG': 'xG', 'RESULTAT': 'AKTION'
                })
                
                st.dataframe(
                    vis_df, 
                    hide_index=True, 
                    use_container_width=True, 
                    height=min(len(vis_df) * 35 + 38, 500),
                    column_config={
                        "#": st.column_config.NumberColumn(width=28),
                        "SPILLER": st.column_config.Column(width=138),
                        "MIN": st.column_config.NumberColumn(width=30),
                        "xG": st.column_config.NumberColumn(width=50, format="%.2f"),
                        "AKTION": st.column_config.Column(width=55)
                    }
                )
            else:
                st.write("Ingen data fundet.")
                
        # 3. Statistik Boks med Konverteringsrate
        total_shots = len(df_p)
        total_goals = int(df_p['IS_GOAL'].sum())
        total_xg = df_p['SHOTXG'].sum()
        conv_rate = (total_goals / total_shots * 100) if total_shots > 0 else 0

        st.markdown(f"""
        <div style="border-left: 5px solid {HIF_RED}; padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
            <h3 style="margin:0; color: #333;">{overskrift}</h3>
            <hr style="margin: 10px 0;">
            <small style="color:gray; text-transform:uppercase;">Viste afslutninger / Mål</small>
            <h2 style="margin:0;">{total_shots} / {total_goals}</h2>
            <div style="margin: 10px 0;"></div>
            <small style="color:gray; text-transform:uppercase;">Konverteringsrate</small>
            <h2 style="margin:0;">{conv_rate:.1f}%</h2>
            <div style="margin: 10px 0;"></div>
            <small style="color:gray; text-transform:uppercase;">Total xG (Filter)</small>
            <h2 style="margin:0;">{total_xg:.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col_map:
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        if not df_p.empty:
            for _, row in df_p.iterrows():
                is_goal = row['IS_GOAL']
                sc_size = (row['SHOTXG'] * 600) + 100
                color = HIF_RED if is_goal else HIF_BLUE
                
                pitch.scatter(row['LOCATIONX'], row['LOCATIONY'], 
                              s=sc_size, edgecolors='white',
                              c=color,
                              marker='o', ax=ax, zorder=3, alpha=0.8)
                
                ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['NR'])), 
                        color='white', ha='center', va='center', 
                        fontsize=7, fontweight='bold', zorder=4)

        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Mål', 
                   markerfacecolor=HIF_RED, markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Skud', 
                   markerfacecolor=HIF_BLUE, markersize=10)
        ]
        
        ax.legend(handles=legend_elements, loc='lower left', bbox_to_anchor=(0, 1.01),
                  ncol=2, fontsize=10, frameon=False)
        
        st.pyplot(fig)
