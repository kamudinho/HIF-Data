import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere):
    st.title("🎥 HIF Videoanalyse")

    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error(f"CSV ikke fundet på {csv_path}")
        return

    # 1. Læs CSV og tving EVENT_WYID til at være rene tal-strenge
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Vi bruger regex \d+ til kun at trække tallene ud fra CSV-kolonnen
    df['EVENT_WYID_CLEAN'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x)))

    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
        if video_filer:
            # 2. Lav et "Vaske-map" for videoerne
            # Vi tager filnavnet '154648614‎.mp4' og trækker KUN tallene ud
            video_map = {}
            for f in video_filer:
                clean_id = "".join(re.findall(r'\d+', f))
                video_map[clean_id] = f
            
            # Lav dropdown baseret på de rensede ID'er
            valgt_id = st.selectbox("Vælg sekvens:", options=list(video_map.keys()))
            
            # 3. Find matchet i CSV
            match_data = df[df['EVENT_WYID_CLEAN'] == valgt_id]

            if not match_data.empty:
                row = match_data.iloc[0]
                st.markdown(f"### 🏟️ {row.get('MATCHLABEL', 'Kamp-info')}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Resultat", row.get('RESULT', 'N/A'))
                c2.metric("xG", f"{float(row.get('SHOTXG', 0)):.2f}")
                c3.metric("Mål", "JA" if str(row.get('SHOTISGOAL')).lower() == 'true' else "NEJ")
                
                # Afspil videoen ved at bruge det originale "beskidte" filnavn fra mappet
                st.video(os.path.join(video_dir, video_map[valgt_id]))
            else:
                st.error(f"❌ ID {valgt_id} blev ikke fundet i CSV.")
                st.write("ID'er i din CSV:", df['EVENT_WYID_CLEAN'].unique())
        else:
            st.info("Ingen .mp4 filer fundet.")
