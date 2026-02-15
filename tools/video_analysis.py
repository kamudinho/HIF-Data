import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere):
    st.title("HIF Analyse-dashboard")
    
    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error("Kunne ikke finde matches.csv")
        return

    # 1. Indlæs og forbered data
    df = pd.read_csv(csv_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Rens ID'er til video-match
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x)))

    # 2. Find videoer i mappen
    video_map = {}
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        for f in video_filer:
            clean_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
            video_map[clean_id] = f

    # 3. Filtrer data til tabellen
    # Vi viser kun rækker, hvor der findes en video
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    # Vælg kun de ønskede kolonner
    vis_cols = ['EVENT_WYID', 'MATCHLABEL', 'SHOTBODYPART', 'SHOTISGOAL', 'SHOTXG', 'DATE', 'VENUE']
    tabel_df = tabel_df[vis_cols]

    # 4. Tabel-visning (Helt almindelig tabel)
    st.subheader("Sekvenser")
    
    # Mulighed for at vælge video via ID fra tabellen
    valgt_event = st.selectbox("Vælg ID for at afspille video", 
                               options=tabel_df['EVENT_WYID'].unique())

    # Vis selve tabellen uden ikoner
    st.dataframe(
        tabel_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "EVENT_WYID": "ID",
            "MATCHLABEL": "Kamp",
            "SHOTBODYPART": "Kropsdel",
            "SHOTISGOAL": "Maal",
            "SHOTXG": "xG",
            "DATE": "Dato",
            "VENUE": "Bane"
        }
    )

    # 5. Afspil video nederst
    if valgt_event:
        clean_id = "".join(re.findall(r'\d+', str(valgt_event)))
        if clean_id in video_map:
            st.write(f"Afspiller video for ID: {valgt_event}")
            st.video(os.path.join(video_dir, video_map[clean_id]))
