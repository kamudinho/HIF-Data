import streamlit as st
import pandas as pd
import os

def vis_side(spillere):
    st.title("🎥 Videoanalyse & Kampdata")

    # 1. Stier
    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    # 2. Hent CSV data
    if os.path.exists(csv_path):
        # Vi tvinger EVENT_WYID til at være tekst (string) for at undgå komma-fejl
        df = pd.read_csv(csv_path)
        df['EVENT_WYID'] = df['EVENT_WYID'].astype(str).str.strip()
    else:
        st.error("Kunne ikke finde data/matches.csv")
        return

    # 3. Find og vis videoer
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
        if video_filer:
            valgt_video = st.selectbox("Vælg sekvens:", video_filer)
            
            # Her kobler vi: Vi fjerner '.mp4' så vi har det rene ID
            id_fra_video = valgt_video.replace(".mp4", "").strip()
            
            # Find rækken i CSV hvor ID matcher
            match_data = df[df['EVENT_WYID'] == id_fra_video]

            if not match_data.empty:
                row = match_data.iloc[0]
                
                # VIS DATA PÆNT
                st.markdown(f"### 🏟️ {row['MATCHLABEL']}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Resultat", row['SCORE'])
                c2.metric("xG", f"{row['SHOTXG']:.2f}")
                c3.metric("Afslutning", row['SHOTBODYPART'])
                
                st.write(f"**Dato:** {row['DATE']} | **Side:** {row['SIDE']}")
            else:
                st.warning(f"Kunne ikke finde data i CSV for video-ID: {id_fra_video}")
            
            # 4. Afspil Video
            video_stien = os.path.join(video_dir, valgt_video)
            st.video(video_stien)
        else:
            st.info("Upload videoer til /videos mappen på GitHub (navngivet efter EVENT_WYID)")
