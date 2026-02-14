import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere):
    st.title("🎥 Videoanalyse & Kampdata")

    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    # 1. Hent og rens CSV data
    if os.path.exists(csv_path):
        # Vi læser filen uden at gætte på separatorer først
        df = pd.read_csv(csv_path, sep=None, engine='python')
        
        # Rens kolonnenavne (fjern mellemrum og gør dem store)
        df.columns = [c.strip().upper() for c in df.columns]
        
        # VIGTIGT: Rens EVENT_WYID kolonnen for ALT andet end tal
        if 'EVENT_WYID' in df.columns:
            df['EVENT_WYID_CLEAN'] = df['EVENT_WYID'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
        else:
            st.error("Kolonnen 'EVENT_WYID' blev ikke fundet i CSV-filen.")
            st.write("Fundne kolonner:", list(df.columns))
            return
    else:
        st.error(f"Kunne ikke finde {csv_path}")
        return

    # 2. Hent og rens videofiler
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
        if video_filer:
            # Vi laver en ordbog, der mapper det rensede ID til det faktiske filnavn
            video_map = {}
            for f in video_filer:
                clean_id = re.sub(r'\D', '', f) # Fjerner .mp4 OG de usynlige tegn
                video_map[clean_id] = f

            valgt_clean_id = st.selectbox(
                "Vælg sekvens:", 
                options=list(video_map.keys()),
                format_func=lambda x: f"Sekvens ID: {x}"
            )
            
            # 3. Find match i CSV
            match_data = df[df['EVENT_WYID_CLEAN'] == valgt_clean_id]

            if not match_data.empty:
                row = match_data.iloc[0]
                
                st.markdown(f"### 🏟️ {row.get('MATCHLABEL', 'Kamp-info')}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Resultat", row.get('SCORE', 'N/A'))
                c2.metric("xG", row.get('SHOTXG', '0.00'))
                c3.metric("Kropsdel", row.get('SHOTBODYPART', 'N/A'))
                
                st.write(f"**Dato:** {row.get('DATE', 'N/A')} | **Venue:** {row.get('VENUE', 'N/A')}")
            else:
                st.warning(f"ID {valgt_clean_id} ikke fundet i matches.csv")
                if st.checkbox("Vis rå data fra CSV"):
                    st.write(df[['EVENT_WYID', 'EVENT_WYID_CLEAN']].head())
            
            # 4. Afspil Video (bruger det originale filnavn fra mappet)
            st.video(os.path.join(video_dir, video_map[valgt_clean_id]))
        else:
            st.info("Ingen .mp4 filer fundet i /videos mappen.")
    else:
        st.error(f"Mappen '{video_dir}' blev ikke fundet.")
