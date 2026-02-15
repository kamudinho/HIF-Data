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
    
    # Tving EVENT_WYID til at være tekst med det samme for at undgå .0 decimaler eller punktummer
    df['EVENT_WYID'] = df['EVENT_WYID'].astype(str).str.replace('.0', '', regex=False)
    
    # Lav rensede ID'er til video-match (kun tal)
    df['RENS_ID'] = df['EVENT_WYID'].apply(lambda x: "".join(re.findall(r'\d+', x)))

    # 2. Find alle videoer i mappen
    video_map = {}
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        for f in video_filer:
            # Rens filnavnet for alt andet end tal (fjerner .mp4 og usynlige tegn)
            clean_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
            video_map[clean_id] = f

    # 3. Filtrer data til tabellen (vis kun dem vi har video til)
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    if tabel_df.empty:
        st.info("Ingen matchende videoer fundet i mappen. Tjek om filnavnene matcher ID'erne i CSV'en.")
        return

    vis_cols = ['EVENT_WYID', 'MATCHLABEL', 'SHOTBODYPART', 'SHOTISGOAL', 'SHOTXG', 'DATE', 'VENUE']
    tabel_df = tabel_df[vis_cols]

    # 4. Tabel-visning
    st.subheader("Sekvenser")
    
    # Selectboxen bruger nu de rene tekst-ID'er
    # format_func sørger for at fjerne eventuelle tusindtalsseparatorer i visningen
    valgt_event = st.selectbox(
        "Vælg ID for at afspille video", 
        options=tabel_df['EVENT_WYID'].unique(),
        format_func=lambda x: str(x).replace(',', '').replace('.', '')
    )

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

    # 5. Afspil video (Rens valgt_event igen for en sikkerheds skyld)
    if valgt_event:
        search_id = "".join(re.findall(r'\d+', str(valgt_event)))
        if search_id in video_map:
            st.write(f"Afspiller video for ID: {search_id}")
            video_sti = os.path.join(video_dir, video_map[search_id])
            st.video(video_sti)
        else:
            st.error(f"Kunne ikke finde videofilen for ID: {search_id}")
            # Debug hjælp:
            if st.checkbox("Vis teknisk info for fejlfinding"):
                st.write("Søgte efter ID:", search_id)
                st.write("Tilgængelige video-ID'er i mappe:", list(video_map.keys())[:10])
