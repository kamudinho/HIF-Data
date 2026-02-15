import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # --- 1. OPSÆTNING AF STIER ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        st.error(f"Kunne ikke finde matches.csv i {match_path}")
        return

    # --- 2. DATA-HENTNING OG RENSNING ---
    # Vi indlæser matches.csv som indeholder alle kamps- og skuddata
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    # Vi renser spillere_df (som kommer fra din hovedfil) for at kunne mappe navne
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    
    # Lav navne-map (ID -> NAVN)
    if 'NAVN' in spillere_df.columns:
        navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df['NAVN']))
    else:
        fn = spillere_df.get('FIRSTNAME', '').fillna('')
        ln = spillere_df.get('LASTNAME', '').fillna('')
        spillere_df['FULL_NAME'] = (fn + ' ' + ln).str.strip()
        navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df['FULL_NAME']))

    # Rens ID'er i match-data så de matcher både spillere og videofiler
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna(df['PLAYER_WYID'])
    # RENS_ID fjerner alt andet end tal fra EVENT_WYID (ID'et der matcher videoen)
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # --- 3. VIDEO-HENTNING (Fixer .mp4 fejlen) ---
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                # VIGTIGT: Vi splitter filendelsen .mp4 fra FØR vi finder tal
                filnavn_uden_endelse = os.path.splitext(f)[0]
                clean_id = "".join(re.findall(r'\d+', filnavn_uden_endelse))
                video_map[clean_id] = f

    # --- 4. FILTRERING ---
    # Find kun rækker hvor der rent faktisk findes en video
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    # Sidebar toggle til at filtrere på mål
    kun_maal = st.sidebar.toggle("Vis kun mål", value=True)
    if kun_maal and 'SHOTISGOAL' in tabel_df.columns:
        # Tjekker bredt for sand/falsk værdier
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    if tabel_df.empty:
        st.info("Ingen videoer fundet der matcher dine kriterier.")
        return

    # --- 5. VISNING I GRID (4 PR. RÆKKE) ---
    st.write(f"Viser {len(tabel_df)} sekvenser")
    
    # Vi bruger et loop til at opdele vores dataframe i bidder af 4
    for i in range(0, len(tabel_df), 4):
        cols = st.columns(4)
        batch = tabel_df.iloc[i:i+4]
        
        for index, (idx, row) in enumerate(batch.iterrows()):
            with cols[index]:
                # Hent videostien
                v_fil = video_map.get(row['RENS_ID'])
                video_sti = os.path.join(video_dir, v_fil)
                
                # Overskrift (Spillernavn)
                st.markdown(f"**{row['SPILLER']}**")
                
                # Selve videoen (den vises direkte som en thumbnail man kan trykke play på)
                st.video(video_sti)
                
                # Info-tekst under videoen
                st.caption(f"{row['MATCHLABEL']}")
                if 'SHOTXG' in row:
                    st.caption(f"xG: {row['SHOTXG']}")
                
                st.markdown("<br>", unsafe_allow_html=True) # Luft til næste række
