import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # 1. Stier
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        st.error(f"Kunne ikke finde datafilen: {match_path}")
        return

    # 2. Indlæs data
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    # 3. Sammenkobling af spillernavne
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    
    if 'NAVN' in spillere_df.columns:
        navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df['NAVN']))
    else:
        # Hvis NAVN ikke findes, kombinerer vi for- og efternavn
        fn = spillere_df.get('FIRSTNAME', '').fillna('')
        ln = spillere_df.get('LASTNAME', '').fillna('')
        spillere_df['FULL_NAME'] = (fn + ' ' + ln).str.strip()
        navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df['FULL_NAME']))

    # Rens ID'er
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna(df['PLAYER_WYID'])
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # 4. Find videoer (uden .mp4 fejlen)
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                rent_navn = os.path.splitext(f)[0]
                clean_id = "".join(re.findall(r'\d+', rent_navn))
                video_map[clean_id] = f

    # 5. Filtrer til kun rækker med video og kun MÅL som start
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    # Filtrer for mål (SHOTISGOAL skal være True/1)
    tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', 't'])].copy()

    if tabel_df.empty:
        st.warning("Ingen mål med tilhørende video fundet.")
        return

    # 6. Visning med Popover per række
    st.subheader(f"Fundet {len(tabel_df)} mål med video")

    # Overskrift til vores "manuelle" tabel
    h1, h2, h3, h4 = st.columns([2, 3, 1, 2])
    h1.write("**Spiller**")
    h2.write("**Kamp**")
    h3.write("**xG**")
    h4.write("**Video**")
    st.divider()

    # Loop igennem målene og lav en række for hvert
    for idx, row in tabel_df.iterrows():
        c1, c2, c3, c4 = st.columns([2, 3, 1, 2])
        
        c1.write(row['SPILLER'])
        c2.write(row['MATCHLABEL'])
        c3.write(str(row.get('SHOTXG', '-')))
        
        # Popover i kolonne 4
        with c4.popover("Afspil Video", use_container_width=True):
            sid = row['RENS_ID']
            video_fil = video_map.get(sid)
            if video_fil:
                st.write(f"**Aktion:** {row['MATCHLABEL']}")
                st.video(os.path.join(video_dir, video_fil))
            else:
                st.error("Videofilen kunne ikke findes.")
