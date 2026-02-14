import streamlit as st
import pandas as pd
import os

def vis_side():
    st.title("⚽ Videoanalyse fra matches.csv")

    # 1. Sti til data (justeret til din mappe-struktur)
    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error(f"Kunne ikke finde filen: {csv_path}")
        return

    # 2. Læs CSV
    df = pd.read_csv(csv_path)

    # 3. Find videoer
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
        if video_filer:
            valgt_video = st.selectbox("Vælg sekvens:", video_filer)
            
            # Træk ID ud (f.eks. fra '154647763.mp4' til '154647763')
            event_id_fra_fil = valgt_video.replace(".mp4", "")

            # 4. Slå op i CSV (vi tvinger begge til tekst for at matche)
            match_row = df[df['EVENT_WYID'].astype(str) == str(event_id_fra_fil)]

            if not match_row.empty:
                data = match_row.iloc[0]
                
                # Vis data i pæne kasser
                c1, c2, c3 = st.columns(3)
                c1.metric("Kamp", data['MATCHLABEL'])
                c2.metric("Resultat", data['SCORE'])
                c3.metric("xG", data['SHOTXG'])
                
                st.write(f"**Dato:** {data['DATE']} | **Kropsdel:** {data['SHOTBODYPART']}")
            else:
                st.warning(f"Video-ID {event_id_fra_fil} findes ikke i matches.csv")

            # 5. Vis Video
            st.video(os.path.join(video_dir, valgt_video))
        else:
            st.info("Ingen .mp4 filer fundet i /videos mappen.")
    else:
        st.error("Mappen /videos blev ikke fundet.")
