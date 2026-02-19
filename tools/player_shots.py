import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- 0. DYNAMISK IMPORT FRA DIN SEASON_SHOW ---
try:
    from data.season_show import TEAM_WYID, SEASONNAME
    # Vi sætter en standardfarve, da den ikke er i din season_show endnu
    HIF_RED = '#d31313' 
except ImportError:
    TEAM_WYID = 38331
    SEASONNAME = "2025/2026"
    HIF_RED = '#d31313'

def vis_side(df_shots, df_spillere, hold_map):
    # --- 1. CSS TIL OPTIMERING ---
    st.markdown("""
        <style>
            .main .block-container { padding-bottom: 1rem; padding-top: 2rem; }
            footer {display: none;}
            div[data-testid="stSelectbox"] { margin-bottom: -10px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA-PROCESSERING (Fra Snowflake via data_load) ---
    if df_shots is None or df_shots.empty:
        st.warning(f"Ingen skuddata fundet i Snowflake for sæsonen {SEASONNAME}.")
        return

    df_s = df_shots.copy()
    
    # Standardiser kolonnenavne (sikrer vi rammer rigtigt uanset Snowflake setup)
    df_s.columns = [str(c).upper() for c in df_s.columns]
    
    # Tving PLAYER_WYID til string for at matche med spillere.csv
    df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # FILTRERING: Her bruger vi din TEAM_WYID fra season_show.py
    # Vi tjekker både TEAM_WYID og OWNTEAM_WYID (afhængigt af hvad kolonnen hedder i din query)
    team_col = 'TEAM_WYID' if 'TEAM_WYID' in df_s.columns else 'OWNTEAM_WYID'
    if team_col in df_s.columns:
        df_s = df_s[pd.to_numeric(df_s[team_col], errors='coerce') == TEAM_WYID].copy()

    # Navne-mapping fra df_spillere (GitHub CSV)
    s_df = df_spillere.copy()
    s_df.columns = [str(c).upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Sørg for at vi har en NAVN kolonne
    if 'NAVN' not in s_df.columns:
        s_df['NAVN'] = (s_df.get('FIRSTNAME', '').fillna('') + " " + s_df.get('LASTNAME', '').fillna('')).str.strip()
        
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    if df_s.empty:
        st.info(f"Ingen skud registreret for team ID {TEAM_WYID} i {SEASONNAME}.")
        return

    # --- 3. LAYOUT ---
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        st.write("##") 
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        
        valgt_spiller = st.selectbox(
            "Vælg spiller", 
            options=spiller_liste, 
            index=0, 
            label_visibility="collapsed"
        )
        
        df_plot = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
        df_plot = df_plot.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_plot['SHOT_NR'] = df_plot.index + 1

        # Popover med detaljer
        with st.popover(f"Skuddata: {valgt_spiller}", use_container_width=True):
            tabel_df = df_plot.copy()
            tabel_df['RESULTAT'] = tabel_df['SHOTISGOAL'].apply(
                lambda x: "⚽ MÅL" if str(x).lower() in ['true', '1', '1.0', 't'] else "Skud"
            )
            # Vi bruger MATCHLABEL fra Snowflake joinen
            vis_tabel = tabel_df[['SHOT_NR', 'MATCHLABEL', 'MINUTE', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Kamp', 'Min.', 'Res.']
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        # Metrics
        SHOTS = len(df_plot)
        GOALS = int(df_plot['SHOTISGOAL'].apply(lambda x: str(x).lower() in ['true', '1', '1.0', 't']).sum())
        XG_TOTAL = df_plot['SHOTXG'].sum() if 'SHOTXG' in df_plot.columns else 0

        def custom_metric(label, value):
            st.markdown(f"""
                <div style="margin-bottom: 12px; border-left: 2px solid {HIF_RED}; padding-left: 12px;">
                    <p style="margin:0; font-size: 14px; color: #777; text-transform: uppercase;">{label}</p>
                    <p style="margin:0; font-size: 24px; font-weight: 700; color: #222;">{value}</p>
                </div>
            """, unsafe_allow_html=True)

        custom_metric("Afslutninger", SHOTS)
        custom_metric("Mål", GOALS)
        custom_metric("Expected Goals (xG)", f"{XG_TOTAL:.2f}")

    with layout_venstre:
        # Pitch setup med VerticalPitch
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2, pad_bottom=0)
        fig, ax = pitch.draw(figsize=(6, 5))
        ax.set_ylim(45, 102) 

        for _, row in df_plot.iterrows():
            is_goal = str(row.get('SHOTISGOAL', 'false')).lower() in ['true', '1', '1.0', 't']
            
            # Scatter plot for skud
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=200 if is_goal else 150,
                       color='gold' if is_goal else HIF_RED, 
                       edgecolors='white', 
                       linewidth=1.2 if is_goal else 0.5, 
                       alpha=0.9, zorder=3)
            
            # Nummerering
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NR'])), 
                    color='black' if is_goal else 'white', 
                    ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
