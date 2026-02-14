import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere):
    st.title("🎥 Videoanalyse & Kampdata")

    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if os.path.exists(csv_path):
        # Vi læser CSV. Hvis dine kommaer driller i filen, 
        # tvinger vi den til at læse EVENT_WYID korrekt.
        df = pd.read_csv(csv_path)
        
        # RENSNING AF KOLONNER:
        # Vi fjerner alt rod og sørger for at EVENT_WYID er en ren talkæde
        df['EVENT_WYID'] = df['EVENT_WYID'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
    else:
        st.error(f"Kunne ikke finde {csv_path}")
        return

    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
        if video_filer:
            valgt_video = st.selectbox("Vælg sekvens:", video_filer)
            
            # Rens ID fra filnavnet (fjern .mp4 og eventuelle usynlige tegn)
            id_fra_video = re.sub(r'\D', '', valgt_video)
            
            # Søg i din dataframe
            match_data = df[df['EVENT_WYID'] == id_fra_video]

            if not match_data.empty:
                row = match_data.iloc[0]
                
                # Hvis dine kolonner er forskudt i CSV, kan vi kalde dem ved nummer i stedet for navn
                # row.iloc[0] = Matchlabel, row.iloc[1] = Score, osv.
                
                st.markdown(f"### 🏟️ {row.get('MATCHLABEL', 'Kamp-info')}")
                
                c1, c2, c3 = st.columns(3)
                # Vi bruger .get() for en sikkerheds skyld hvis navnet driller
                c1.metric("Resultat", row.get('DATE', 'N/A')) # Fordi din score pt. ligger i Date
                c2.metric("xG", f"{row.get('SHOTXG', 0)}")
                c3.metric("Side", row.get('SIDE', 'N/A'))
                
                st.write(f"**ID:** {id_fra_video}")
            else:
                st.warning(f"ID {id_fra_video} ikke fundet i CSV.")
                # Hjælp til selvhjælp:
                if st.checkbox("Se hvad der står i din CSV"):
                    st.write("Første 5 ID'er i din CSV-fil:")
                    st.write(df['EVENT_WYID'].head())
            
            st.video(os.path.join(video_dir, valgt_video))
