import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.title("HIF Analyse-dashboard")
    
    # Stier til data
    csv_path = 'data/matches.csv'
    players_path = 'data/players.csv' # Vi antager denne sti til spilladata
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error(f"Kunne ikke finde {csv_path}")
        return

    # 1. Indlæs kampsdata
    df = pd.read_csv(csv_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # 2. Indlæs og forbered spillerdata til sammenkobling
    # Vi antager players.csv har kolonnerne PLAYER_WYID og NAVN (eller FIRSTNAME/LASTNAME)
    if os.path.exists(players_path):
        p_df = pd.read_csv(players_path, encoding='utf-8-sig', sep=None, engine='python')
        p_df.columns = [c.strip().upper() for c in p_df.columns]
        
        # Lav en 'NAVN' kolonne hvis den ikke findes (kombiner for- og efternavn)
        if 'NAVN' not in p_df.columns and 'FIRSTNAME' in p_df.columns:
            p_df['NAVN'] = p_df['FIRSTNAME'].fillna('') + ' ' + p_df['LASTNAME'].fillna('')
        
        # Tving ID til tekst for præcis match
        p_df['PLAYER_WYID'] = p_df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
        navne_map = dict(zip(p_df['PLAYER_WYID'], p_df['NAVN']))
    else:
        navne_map = {}
        st.warning("players.csv blev ikke fundet - viser rå ID'er i stedet.")

    # 3. Rens hændelses-ID'er til video-match
    df['EVENT_WYID'] = df['EVENT_WYID'].astype(str).str.replace('.0', '', regex=False)
    df['RENS_ID'] = df['EVENT_WYID'].apply(lambda x: "".join(re.findall(r'\d+', x)))
    
    # Rens PLAYER_WYID og map til Navn
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    df['SPILLER'] = df['PLAYER_WYID'].map(navne_map).fillna(df['PLAYER_WYID'])

    # 4. Find alle videoer i mappen
    video_map = {}
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        for f in video_filer:
            clean_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
            video_map[clean_id] = f

    # 5. Filtrer data (vis kun rækker med video)
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    if tabel_df.empty:
        st.info("Ingen matchende videoer fundet.")
        return

    # Vælg de kolonner vi vil vise (nu med SPILLER i stedet for ID)
    vis_cols = ['EVENT_WYID', 'SPILLER', 'MATCHLABEL', 'SHOTBODYPART', 'SHOTISGOAL', 'SHOTXG', 'DATE', 'VENUE']
    tabel_df = tabel_df[vis_cols]

    # 6. Visning
    st.subheader("Sekvenser")
    
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
            "SPILLER": "Spiller",
            "MATCHLABEL": "Kamp",
            "SHOTBODYPART": "Kropsdel",
            "SHOTISGOAL": "Maal",
            "SHOTXG": "xG",
            "DATE": "Dato",
            "VENUE": "Bane"
        }
    )

    # 7. Afspil video
    if valgt_event:
        search_id = "".join(re.findall(r'\d+', str(valgt_event)))
        if search_id in video_map:
            st.write(f"Afspiller video for: {tabel_df[tabel_df['EVENT_WYID']==valgt_event]['SPILLER'].values[0]}")
            video_sti = os.path.join(video_dir, video_map[search_id])
            st.video(video_sti)
