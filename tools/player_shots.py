import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- 0. DYNAMISK KONFIGURATION ---
try:
    from data.season_show import TEAM_WYID, SEASONNAME
    # Standard HIF farve (kan flyttes til season_show hvis ønsket)
    TEAM_COLOR = '#d31313' 
except ImportError:
    TEAM_WYID = 38331
    SEASONNAME = "2025/2026"
    TEAM_COLOR = '#d31313'

def vis_side(df_shots, df_spillere, hold_map):
    """
    Viser skudkort baseret på Snowflake data (df_shots).
    Sikret mod 'shotevents.csv' fejl.
    """
    
    # --- 1. CSS TIL OPTIMERING ---
    st.markdown("""
        <style>
            .main .block-container { padding-bottom: 1rem; padding-top: 2rem; }
            footer {display: none;}
            div[data-testid="stSelectbox"] { margin-bottom: -10px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. VALIDERING AF DATA FRA MOTOREN ---
    if df_shots is None or df_shots.empty:
        st.warning(f"Ingen skuddata fundet i Snowflake for sæsonen {SEASONNAME}.")
        return

    # Arbejd på en kopi for at undgå SettingWithCopy warnings
    df_s = df_shots.copy()
    df_s.columns = [str(c).upper() for c in df_s.columns]
    
    # Rens Player IDs så de matcher på tværs af kilder
    df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Filtrer til eget hold baseret på TEAM_WYID fra season_show.py
    # Vi tjekker TEAM_WYID kolonnen fra din SQL JOIN
    if 'TEAM_WYID' in df_s.columns:
        df_s = df_s[pd.to_numeric(df_s['TEAM_WYID'], errors='coerce') == TEAM_WYID].copy()

    # Mapping af navne fra players.csv (df_spillere)
    s_df = df_spillere.copy()
    s_df.columns = [str(c).upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Skab fuldt navn hvis det mangler
    if 'NAVN' not in s_df.columns:
        s_df['NAVN'] = (s_df.get('FIRSTNAME', '').fillna('') + " " + s_df.get('LASTNAME', '').fillna('')).str.strip()
        
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    if df_s.empty:
        st.info(f"Der er ikke registreret skud for det valgte hold (ID: {TEAM_WYID}) i denne data-batch.")
        return

    # --- 3. UI LAYOUT ---
    col_map, col_stats = st.columns([2, 1])

    with col_stats:
        st.write("##") # Spacer
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        
        valgt_spiller = st.selectbox(
            "Vælg spiller", 
            options=spiller_liste, 
            index=0, 
            label_visibility="collapsed"
        )
        
        # Filtrer data til valgt spiller
        df_plot = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
        df_plot = df_plot.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_plot['SHOT_NR'] = df_plot.index + 1

        # Tabel over skud (i en popover for at spare plads)
    with st.popover(f"Kampdata: {valgt_spiller}", use_container_width=True):
        tabel_df = df_plot.copy()
        
        # Definer mål-ikon
        tabel_df['RESULTAT'] = tabel_df['SHOTISGOAL'].apply(
            lambda x: "⚽ MÅL" if str(x).lower() in ['true', '1', '1.0', 't'] else "Afslutning"
        )
        
        # Vi runder xG til 2 decimaler (hvis kolonnen findes)
        if 'SHOTXG' in tabel_df.columns:
            tabel_df['XG'] = tabel_df['SHOTXG'].astype(float).round(2)
        else:
            tabel_df['XG'] = 0.0
        
        # Vælg og navngiv kolonner til visning
        vis_tabel = tabel_df[['SHOT_NR', 'MATCHLABEL', 'MINUTE', 'XG', 'RESULTAT']]
        vis_tabel.columns = ['Nr.', 'Kamp', 'Min.', 'xG', 'Resultat']
    
    st.dataframe(vis_tabel, hide_index=True, use_container_width=True)
        # Metrics kasser (Ligner dit Stats/Top5 design)
        SHOTS = len(df_plot)
        GOALS = int(df_plot['SHOTISGOAL'].apply(lambda x: str(x).lower() in ['true', '1', '1.0', 't']).sum())
        XG_TOTAL = df_plot['SHOTXG'].sum() if 'SHOTXG' in df_plot.columns else 0
        
        st.markdown(f"""
            <div style="margin-top:20px; border-left: 4px solid {TEAM_COLOR}; padding-left: 15px; background-color: #f9f9f9; padding-top: 10px; padding-bottom: 10px; border-radius: 0 5px 5px 0;">
                <p style="margin:0; color:gray; font-size:12px; font-weight: bold;">AFSLUTNINGER</p>
                <p style="margin:0; font-size:24px; font-weight:bold; color:#222;">{SHOTS}</p>
                <div style="margin-top:15px;"></div>
                <p style="margin:0; color:gray; font-size:12px; font-weight: bold;">MÅL</p>
                <p style="margin:0; font-size:24px; font-weight:bold; color:#222;">{GOALS}</p>
                <div style="margin-top:15px;"></div>
                <p style="margin:0; color:gray; font-size:12px; font-weight: bold;">EXPECTED GOALS (XG)</p>
                <p style="margin:0; font-size:24px; font-weight:bold; color:#222;">{XG_TOTAL:.2f}</p>
            </div>
        """, unsafe_allow_html=True)

    with col_map:
        # Opsætning af banen (Wyscout koordinater)
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
        fig, ax = pitch.draw(figsize=(6, 5))
        ax.set_ylim(45, 102) # Zoomer ind på modstanderens banehalvdel

        for _, row in df_plot.iterrows():
            is_goal = str(row.get('SHOTISGOAL', 'false')).lower() in ['true', '1', '1.0', 't']
            
            # Tegn skuddet
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=220 if is_goal else 160,
                       color='gold' if is_goal else TEAM_COLOR, 
                       edgecolors='white', 
                       linewidth=1.5 if is_goal else 0.5, 
                       alpha=0.9, zorder=3)
            
            # Skriv nummeret indeni
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NR'])), 
                    color='black' if is_goal else 'white', 
                    ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
