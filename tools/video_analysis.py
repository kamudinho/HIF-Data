import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import re
from mplsoccer import VerticalPitch

# --- 1. VIDEO POPUP FUNKTION ---
@st.dialog("Videoanalyse")
def vis_video_modal(event_id):
    video_dir = 'videos'
    clean_id = "".join(re.findall(r'\d+', str(event_id).replace('.0', '')))
    video_fil = f"{clean_id}.mp4"
    video_sti = os.path.join(video_dir, video_fil)

    if os.path.exists(video_sti):
        st.video(video_sti)
    else:
        st.error(f"Kunne ikke finde videofilen for ID: {clean_id}")

# --- 2. HOVEDFUNKTION ---
def vis_side(df_events, df_spillere, hold_map):
    HIF_RED = '#d31313'

    # DATA-PROCESSERING
    csv_path = 'shotevents.csv'
    if not os.path.exists(csv_path):
        st.error("shotevents.csv mangler!")
        return

    df = pd.read_csv(csv_path)
    df.columns = [c.upper() for c in df.columns]

    # Mapping af spillernavne fra players.csv
    navne_dict = dict(zip(df_spillere['PLAYER_WYID'].astype(str).str.replace('.0','', regex=False), df_spillere['NAVN']))
    df['SPILLER_NAVN'] = df['PLAYER_WYID'].astype(str).str.replace('.0','', regex=False).map(navne_dict).fillna("Ukendt")

    # --- FILTRERING: VIS KUN MÅL SOM STANDARD ---
    # Vi filtrerer så vi kun ser mål (SHOTISGOAL = True)
    df_goals = df[df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', 't'])].copy().reset_index(drop=True)
    df_goals['SHOT_NR'] = df_goals.index + 1

    st.title("Alle Sæsonens Mål")

    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        st.write("### Målliste")
        
        # Popover med tabel over alle mål
        with st.popover("Se alle mål-detaljer", use_container_width=True):
            h = st.columns([1, 3, 2, 2])
            h[0].write("**Nr.**")
            h[1].write("**Spiller / Kamp**")
            h[2].write("**Score**")
            h[3].write("**Video**")
            st.divider()

            for idx, row in df_goals.iterrows():
                r = st.columns([1, 3, 2, 2])
                r[0].write(f"{int(row['SHOT_NR'])}")
                r[1].write(f"**{row['SPILLER_NAVN']}**\n{row['MATCHLABEL']}")
                r[2].write(row['SCORE'])
                
                # Unik knap til video
                if r[3].button("Se video", key=f"goal_btn_{idx}_{row['EVENT_WYID']}"):
                    vis_video_modal(row['EVENT_WYID'])

        # Hurtige stats
        st.divider()
        st.metric("Total antal mål", len(df_goals))
        st.metric("Gns. xG pr. mål", f"{df_goals['SHOTXG'].mean():.2f}")

    with layout_venstre:
        # Bane-tegning
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444')
        fig, ax = pitch.draw(figsize=(6, 5))
        ax.set_ylim(45, 102) 

        # Tegn alle mål på banen
        for _, row in df_goals.iterrows():
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=200, 
                       color='gold', 
                       edgecolors='black', 
                       linewidth=1, 
                       alpha=0.9, zorder=3)
            
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NR'])), 
                    color='black', ha='center', va='center', 
                    fontsize=6, fontweight='bold', zorder=4)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
