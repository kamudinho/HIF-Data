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

    # Læs og rens CSV med det samme
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Rens EVENT_WYID for alt andet end tal og fjern alt usynligt
    df['EVENT_WYID_CLEAN'] = df['EVENT_WYID'].astype(str).str.extract('(\d+)').astype(str)

    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
        if video_filer:
            # Rens filnavne: Vi tager KUN de første 9 cifre, hvis de driller
            video_map = {}
            for f in video_filer:
                clean_id = "".join(re.findall(r'\d+', f))
                video_map[clean_id] = f
            
            valgt_id = st.selectbox("Vælg sekvens:", options=list(video_map.keys()))
            
            # DIAGNOSE (Slet disse når det virker)
            st.write(f"DEBUG: Søger efter ID '{valgt_id}'")
            st.write(f"DEBUG: Findes i CSV? {valgt_id in df['EVENT_WYID_CLEAN'].values}")

            match_data = df[df['EVENT_WYID_CLEAN'] == valgt_id]

            if not match_data.empty:
                row = match_data.iloc[0]
                st.markdown(f"### 🏟️ {row['MATCHLABEL']}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Resultat", row.get('RESULT', 'N/A'))
                c2.metric("xG", row.get('SHOTXG', '0.00'))
                c3.metric("Mål", "JA" if str(row.get('SHOTISGOAL')).lower() == 'true' else "NEJ")
                
                st.video(os.path.join(video_dir, video_map[valgt_id]))
            else:
                st.error(f"❌ ID {valgt_id} blev ikke fundet i CSV.")
                st.write("Tilgængelige ID'er i din CSV:", df['EVENT_WYID_CLEAN'].unique()[:5])
