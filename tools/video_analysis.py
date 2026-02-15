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
        fn = spillere_df.get('FIRSTNAME', '').fillna('')
        ln = spillere_df.get('LASTNAME', '').fillna('')
        spillere_df['FULL_NAME'] = (fn + ' ' + ln).str.strip()
        navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df['FULL_NAME']))

    # Rens ID'er
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna(df['PLAYER_WYID'])
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # 4. Find videoer
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                rent_navn = os.path.splitext(f)[0]
                clean_id = "".join(re.findall(r'\d+', rent_navn))
                video_map[clean_id] = f

    # 5. Filtrer til kun rækker med video
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    if tabel_df.empty:
        st.warning("Ingen videoer fundet i mappen, der matcher ID'erne i matches.csv.")
        return

    # --- NY FILTRERINGSMULIGHED ---
    st.write("### Filtrér visning")
    kun_maal = st.toggle("Vis kun mål", value=True)

    if kun_maal:
        # Robust tjek for 'True', '1', '1.0' osv.
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't'])].copy()

    if tabel_df.empty:
        st.info("Ingen mål fundet med video. Prøv at slå 'Vis kun mål' fra for at se alle aktioner.")
        return

    # 6. Visning med Popover per række
    st.subheader(f"Viser {len(tabel_df)} aktioner")

    # Tabel-headere
    h1, h2, h3, h4 = st.columns([2, 3, 1, 2])
    h1.write("**Spiller**")
    h2.write("**Kamp**")
    h3.write("**xG**")
    h4.write("**Video**")
    st.divider()

    # Loop igennem rækkerne
    for idx, row in tabel_df.iterrows():
        c1, c2, c3, c4 = st.columns([2, 3, 1, 2])
        
        c1.write(row['SPILLER'])
        c2.write(row['MATCHLABEL'])
        c3.write(str(row.get('SHOTXG', '-')))
        
        # Unik key for hver popover baseret på RENS_ID
        with c4.popover("📽️ Se Video", use_container_width=True):
            sid = row['RENS_ID']
            video_fil = video_map.get(sid)
            if video_fil:
                st.write(f"**{row['SPILLER']}** - {row['MATCHLABEL']}")
                st.video(os.path.join(video_dir, video_fil))
            else:
                st.error("Fil mangler")
