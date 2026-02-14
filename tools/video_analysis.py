import streamlit as st
import pandas as pd
import os

def hent_data_fra_csv(event_id):
    # Læs CSV-filen fra din data-mappe
    df = pd.read_csv('data/matches.csv')
    
    # Find den række hvor EVENT_WYID matcher (vi sikrer os at de er samme type)
    match_data = df[df['EVENT_WYID'].astype(str) == str(event_id)]
    
    if not match_data.empty:
        return match_data.iloc[0] # Returner den første (og eneste) række fundet
    return None

def vis_side(spillere):
    st.title("⚽ Kampanalyse (Lokal Data)")

    # Find videoer i din mappe
    video_dir = "videos"
    video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]

    if video_filer:
        valgt_video = st.selectbox("Vælg sekvens:", video_filer)
        
        # Træk EVENT_WYID ud af filnavnet (f.eks. "154647763.mp4")
        event_id = valgt_video.replace(".mp4", "")
        
        # Hent data fra din CSV
        data = hent_data_fra_csv(event_id)
        
        if data is not None:
            # Vis kamp-info i kolonner
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"🏟️ **{data['MATCHLABEL']}**")
                st.write(f"**Dato:** {data['DATE']}")
                st.write(f"**Resultat:** {data['SCORE']}")
            with col2:
                st.success(f"🎯 **Statistik for sekvens**")
                st.write(f"**Afslutning:** {data['SHOTBODYPART']}")
                st.write(f"**xG:** {data['SHOTXG']}")
                st.write(f"**Mål:** {'Ja' if str(data['SHOTISGOAL']).lower() == 'true' else 'Nej'}")
        
        # Vis selve videoen
        video_stien = os.path.join(video_dir, valgt_video)
        st.video(video_stien)
    else:
        st.warning("Ingen videoer fundet i /videos mappen.")
