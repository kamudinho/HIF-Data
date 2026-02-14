import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere):
    st.title("🎥 HIF Videoanalyse")

    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error(f"Kunne ikke finde filen: {csv_path}")
        return

    # 1. Læs CSV og rens alt med det samme
    # Vi bruger 'sep=None' så den selv finder ud af om det er komma eller semikolon
    df = pd.read_csv(csv_path, sep=None, engine='python')
    
    # Rens kolonnenavne for usynlige tegn og gør dem store
    df.columns = [re.sub(r'\W+', '', c).upper() for c in df.columns]
    
    # Lav en "RENS_ID" kolonne hvor vi fjerner alt rod fra EVENT_WYID
    if 'EVENT_WYID' in df.columns:
        df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x)))
    else:
        st.error("Kunne ikke finde kolonnen EVENT_WYID. Tjek overskriften i din CSV.")
        st.write("Jeg fandt disse kolonner:", list(df.columns))
        return

    # 2. Håndter videoerne
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
        if video_filer:
            # Lav et map: { "RensetID": "OriginaltFilnavn" }
            # Det fjerner de usynlige tegn fra GitHub-filnavnet
            video_map = { "".join(re.findall(r'\d+', f)): f for f in video_filer }
            
            valgt_id = st.selectbox("Vælg sekvens (ID):", options=list(video_map.keys()))
            
            # 3. Find matchet i dine 5500 rækker
            match_data = df[df['RENS_ID'] == valgt_id]

            if not match_data.empty:
                row = match_data.iloc[0]
                
                # Dynamisk visning - vi tager hvad vi kan finde
                st.markdown(f"### 🏟️ {row.get('MATCHLABEL', 'Kamp-info')}")
                
                c1, c2, c3 = st.columns(3)
                # Vi bruger .get() så koden ikke dør hvis en kolonne mangler
                c1.metric("Resultat", row.get('RESULT', row.get('SCORE', 'N/A')))
                c2.metric("xG", row.get('SHOTXG', '0.00'))
                c3.metric("Kropsdel", row.get('SHOTBODYPART', 'N/A'))
                
                st.video(os.path.join(video_dir, video_map[valgt_id]))
            else:
                st.error(f"❌ ID {valgt_id} findes i din videomappe, men IKKE i din CSV.")
                # Vis de første 5 ID'er fra CSV til sammenligning
                st.write("ID'er jeg kan se i din CSV:", df['RENS_ID'].unique()[:5])
        else:
            st.info("Ingen videoer fundet i /videos mappen.")
