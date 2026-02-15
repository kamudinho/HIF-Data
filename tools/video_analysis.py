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
        st.error("Data mangler: matches.csv blev ikke fundet.")
        return

    # --- 2. DATA HENTNING & MAPPING ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Map navne fra spillere_df
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna("Ukendt")
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # Find videoer
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                vid_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
                video_map[vid_id] = f

    # Filtrer
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    if st.sidebar.toggle("Vis kun mål", value=True):
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    # --- 3. TABEL VISNING MED POPOVER & TABS ---
    st.markdown("---")
    # Overskrifter
    h1, h2, h3, h4 = st.columns([2, 3, 1, 2])
    h1.write("**Spiller**")
    h2.write("**Kamp**")
    h3.write("**xG**")
    h4.write("**Analyse**")
    st.divider()

    for idx, row in tabel_df.iterrows():
        c1, c2, c3, c4 = st.columns([2, 3, 1, 2])
        
        c1.write(f"**{row['SPILLER']}**")
        c2.write(row['MATCHLABEL'])
        c3.write(str(row.get('SHOTXG', '-')))
        
        with c4:
            # Popover ligesom i din scouting_db
            with st.popover("Åbn Analyse", use_container_width=True):
                # Tabs indeni popoveren
                tab_video, tab_billede = st.tabs(["🎥 Video", "📊 Statistik"])
                
                with tab_video:
                    v_fil = video_map.get(row['RENS_ID'])
                    video_sti = os.path.join(video_dir, v_fil)
                    st.video(video_sti)
                    st.caption(f"Klip: {row['SPILLER']} vs {row['MATCHLABEL']}")
                
                with tab_billede:
                    # Her kan du indsætte et billede. 
                    # Som eksempel bruger jeg et placeholder-billede af en bane
                    st.image("https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=500", 
                             caption="Position og Stats")
                    st.write(f"**Spiller ID:** {row['PLAYER_WYID']}")
                    st.write(f"**Event ID:** {row['EVENT_WYID']}")

        st.divider()
