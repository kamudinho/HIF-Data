import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import re
from mplsoccer import VerticalPitch

# --- 1. VIDEO POPUP FUNKTION ---
@st.dialog("Videoanalyse")
def vis_video_modal(event_id):
    video_dir = 'videos'
    # Vi sikrer os at ID'et er rent (fjerner .0 og usynlige tegn)
    clean_id = "".join(re.findall(r'\d+', str(event_id).replace('.0', '')))
    video_fil = f"{clean_id}.mp4"
    video_sti = os.path.join(video_dir, video_fil)

    if os.path.exists(video_sti):
        st.video(video_sti)
    else:
        st.error(f"Kunne ikke finde videofilen for ID: {clean_id}")

# --- 2. HOVEDFUNKTION ---
def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'

    # CSS til optimering
    st.markdown("""
        <style>
            .main .block-container { padding-bottom: 1rem; padding-top: 2rem; }
            footer {display: none;}
            div[data-testid="stSelectbox"] { margin-bottom: -10px; }
        </style>
    """, unsafe_allow_html=True)

    # DATA-PROCESSERING
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SHOT_CSV_PATH = os.path.join(BASE_DIR, 'shotevents.csv')

    if not os.path.exists(SHOT_CSV_PATH):
        st.error("Kunne ikke finde shotevents.csv")
        return

    # Indlæs og rens skud-data
    df_s = pd.read_csv(SHOT_CSV_PATH)
    df_s.columns = [str(c).strip().upper() for c in df_s.columns]
    df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Filtrer til HIF
    if 'TEAM_WYID' in df_s.columns:
        df_s = df_s[pd.to_numeric(df_s['TEAM_WYID'], errors='coerce').fillna(0).astype(int) == HIF_ID].copy()

    # Navne-mapping
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    s_df['FULL_NAME'] = s_df.apply(
        lambda x: f"{x.get('FIRSTNAME', '')} {x.get('LASTNAME', '')}".strip() 
        if pd.notna(x.get('FIRSTNAME')) or pd.notna(x.get('LASTNAME')) 
        else x.get('NAVN', "-"), axis=1
    )
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['FULL_NAME']))

    # Tving numeriske værdier
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce')
    
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    # Berig data
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")
    df_s['MODSTANDER'] = df_s['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(float(x)), f"Hold {x}") if pd.notna(x) else "Ukendt")
    df_s = df_s.sort_values(by=['MODSTANDER', 'MINUTE']).reset_index(drop=True)

    # LAYOUT
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        st.write("##") 
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=spiller_liste, index=0, label_visibility="collapsed")
        
        # Filter til spiller
        df_plot = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
        df_plot = df_plot.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_plot['SHOT_NR'] = df_plot.index + 1

        # Popover med tabel (uden ikoner)
        with st.popover(f"Skuddata: {valgt_spiller}", use_container_width=True):
            h1, h2, h3, h4 = st.columns([1, 3, 2, 2])
            h1.write("**Nr.**")
            h2.write("**Modstander**")
            h3.write("**Resultat**")
            h4.write("**Video**")
            st.divider()

            for _, row in df_plot.iterrows():
                r1, r2, r3, r4 = st.columns([1, 3, 2, 2])
                is_goal = str(row.get('SHOTISGOAL')).lower() in ['true', '1', '1.0', 't']
                
                r1.write(f"{int(row['SHOT_NR'])}")
                r2.write(row['MODSTANDER'])
                r3.write("MAAL" if is_goal else "Skud")
                
                # Video-knap uden ikon
                if r4.button("Se video", key=f"btn_{row.get('EVENT_WYID')}"):
                    vis_video_modal(row.get('EVENT_WYID'))

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        # Metrics
        SHOTS = len(df_plot)
        GOALS = int(df_plot['SHOTISGOAL'].apply(lambda x: str(x).lower() in ['true', '1', '1.0', 't']).sum())
        ON_TARGET = int(df_plot['SHOTONTARGET'].apply(lambda x: str(x).lower() in ['true', '1', '1.0', 't']).sum())
        XG_TOTAL = df_plot['SHOTXG'].sum()
        AVG_DIST = (100 - df_plot['LOCATIONX']).mean() if SHOTS > 0 else 0

        def custom_metric(label, value):
            st.markdown(f"""
                <div style="margin-bottom: 12px; border-left: 2px solid {HIF_RED}; padding-left: 12px;">
                    <p style="margin:0; font-size: 14px; color: #777; text-transform: uppercase;">{label}</p>
                    <p style="margin:0; font-size: 22px; font-weight: 700; color: #222;">{value}</p>
                </div>
            """, unsafe_allow_html=True)

        custom_metric("Afslutninger", SHOTS)
        custom_metric("Maal", GOALS)
        custom_metric("Konverteringsrate", f"{(GOALS / SHOTS * 100) if SHOTS > 0 else 0:.1f}%")
        custom_metric("Skud paa maal", ON_TARGET)
        custom_metric("Expected Goals (xG)", f"{XG_TOTAL:.2f}")
        custom_metric("Gns. Afstand", f"{AVG_DIST:.1f} m")

    with layout_venstre:
        # Pitch tegning
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2, pad_bottom=0)
        fig, ax = pitch.draw(figsize=(6, 5))
        ax.set_ylim(45, 102) 

        for _, row in df_plot.iterrows():
            is_goal = str(row.get('SHOTISGOAL', 'false')).lower() in ['true', '1', '1.0', 't']
            
            # Scatter plot af skud
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=180,
                       color='gold' if is_goal else HIF_RED, 
                       edgecolors='white', 
                       linewidth=1.2 if is_goal else 0.5, 
                       alpha=0.9, zorder=3)
            
            # Nummerering på banen
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NR'])), 
                    color='black' if is_goal else 'white', 
                    ha='center', va='center', fontsize=5, fontweight='bold', zorder=4)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
