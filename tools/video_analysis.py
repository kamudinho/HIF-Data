import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere):
    st.title("🎥 HIF Videoanalyse")

    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    # 1. Hent og klargør CSV
    if os.path.exists(csv_path):
        # Vi læser CSV og tvinger EVENT_WYID til at være tekst uden usynlige tegn
        df = pd.read_csv(csv_path)
        df.columns = [c.strip().upper() for c in df.columns] # Gør kolonner store og rene
        
        if 'EVENT_WYID' in df.columns:
            df['EVENT_WYID_CLEAN'] = df['EVENT_WYID'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
        else:
            st.error("Fejl: Kolonnen 'EVENT_WYID' mangler i din CSV!")
            return
    else:
        st.error(f"Kunne ikke finde filen: {csv_path}")
        return

    # 2. Hent videofiler og rens deres navne for usynlige tegn
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
        if video_filer:
            # Vi mapper 'rent_id' -> 'originalt_filnavn' for at ramme de korrupte GitHub-navne
            video_map = {re.sub(r'\D', '', f): f for f in video_filer}
            
            # Lav en pæn liste til dropdown (kun de rene numre)
            valgt_id = st.selectbox("Vælg sekvens (Event ID):", options=list(video_map.keys()))
            
            # 3. Find data i CSV
            match_data = df[df['EVENT_WYID_CLEAN'] == valgt_id]

            if not match_data.empty:
                row = match_data.iloc[0]
                
                # VISNING AF DATA
                st.markdown(f"### 🏟️ {row['MATCHLABEL']}")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Resultat", row.get('RESULT', 'N/A'))
                c2.metric("xG", f"{float(row.get('SHOTXG', 0)):.2f}")
                c3.metric("Kropsdel", row.get('SHOTBODYPART', 'N/A'))
                c4.metric("Mål", "JA" if str(row.get('SHOTISGOAL')).lower() == 'true' else "NEJ")
                
                st.info(f"📅 **Dato:** {row.get('DATE')}  |  📍 **Side:** {row.get('SIDE')}")
            else:
                st.warning(f"Ingen data fundet i CSV for ID: {valgt_id}")

            # 4. Afspil Video (bruger det originale filnavn fra mappet)
            st.video(os.path.join(video_dir, video_map[valgt_id]))
        else:
            st.info("Ingen .mp4 filer fundet i /videos mappen.")
    else:
        st.error("Mappen /videos blev ikke fundet.")
