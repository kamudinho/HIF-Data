import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere):
    st.title("⚽ HIF Analyse-dashboard")
    
    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error("Kunne ikke finde matches.csv")
        return

    # 1. Indlæs data
    # Vi bruger utf-8-sig for at håndtere de danske tegn korrekt
    df = pd.read_csv(csv_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Lav rensede ID'er til match mod videofiler
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x)))

    # 2. Find alle tilgængelige videoer
    video_map = {}
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        for f in video_filer:
            # Fjern .mp4 før rensning for at undgå det ekstra 4-tal
            clean_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
            video_map[clean_id] = f

    # 3. Oversigtstabel
    st.subheader("Oversigt over afslutninger")
    
    # Vi filtrerer, så vi kun ser rækker, hvor der rent faktisk er en video
    video_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    if video_df.empty:
        st.info("Ingen matchende videoer fundet i mappen.")
        return

    # Overskrifter til tabellen
    t_cols = st.columns([1, 3, 1, 2, 1, 1])
    t_cols[0].write("**Video**")
    t_cols[1].write("**Kamp**")
    t_cols[2].write("**Resultat**")
    t_cols[3].write("**Kropsdel**")
    t_cols[4].write("**Mål**")
    t_cols[5].write("**xG**")
    st.divider()

    # Loop gennem data og map efter din nye struktur
    for idx, row in video_df.iterrows():
        c = st.columns([1, 3, 1, 2, 1, 1])
        
        # Knap til popup
        if c[0].button("▶️", key=f"btn_{row['RENS_ID']}"):
            vis_video_popup(row, video_map.get(row['RENS_ID']), video_dir)
            
        c[1].write(row.get('MATCHLABEL', 'N/A'))
        c[2].write(row.get('RESULT', 'N/A'))
        
        # OVERSÆTTELSE AF KOLONNER (Jvf. din beskrivelse):
        # Kropsdel ligger i 'SHOTBODYPART'
        c[3].write(row.get('SHOTBODYPART', 'N/A'))
        
        # Mål (True/False) ligger i 'SHOTISGOAL'
        er_maal = str(row.get('SHOTISGOAL')).lower() == 'true'
        c[4].write("⚽ JA" if er_maal else "❌")
        
        # xG værdi ligger i 'SHOTXG'
        xg_val = row.get('SHOTXG', '0.00')
        c[5].write(f"{xg_val}")

# 4. Popup vinduet med korrekt oversættelse
@st.dialog("Videoanalyse")
def vis_video_popup(data, filnavn, video_dir):
    st.subheader(f"{data.get('MATCHLABEL', 'Kamp-data')}")
    
    if filnavn:
        st.video(os.path.join(video_dir, filnavn))
    
    st.divider()
    
    # Her mapper vi værdierne præcis efter din nye rækkefølge
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Resultat:** {data.get('RESULT', 'N/A')}")
        st.write(f"**Side (H/A):** {data.get('SIDE', 'N/A')}")
        st.write(f"**Kropsdel:** {data.get('SHOTBODYPART', 'N/A')}")
        
    with col2:
        # Mål ligger i 'SHOTISGOAL'
        er_maal = str(data.get('SHOTISGOAL')).lower() == 'true'
        st.write(f"**Mål:** {'✅ JA' if er_maal else '❌ NEJ'}")
        
        # xG ligger i 'SHOTXG'
        st.metric("xG Værdi", f"{data.get('SHOTXG', '0.00')}")
        
        # Dato ligger i 'DATE'
        st.write(f"📅 **Dato:** {data.get('DATE', 'N/A')}")

    if st.button("Luk"):
        st.rerun()
