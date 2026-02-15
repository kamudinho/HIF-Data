import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # 1. Konfiguration af stier
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        st.error("Kunne ikke finde matches.csv")
        return

    # 2. Dataforberedelse
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    # Map spillernavne
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna("Ukendt Spiller")
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # 3. Match videoer (sikrer at vi ikke stjæler 4-tallet fra .mp4)
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                rent_navn = os.path.splitext(f)[0]
                clean_id = "".join(re.findall(r'\d+', rent_navn))
                video_map[clean_id] = f

    # 4. Filtrering
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    # Toggle i sidebaren
    kun_maal = st.sidebar.toggle("Vis kun mål", value=True)
    if kun_maal and 'SHOTISGOAL' in tabel_df.columns:
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    if tabel_df.empty:
        st.info("Ingen videoer fundet.")
        return

    # --- 5. DIREKTE VIDEO GRID (4 PR. RÆKKE) ---
    st.write(f"Viser {len(tabel_df)} klip")
    
    # Vi looper gennem data i rækker af 4
    for i in range(0, len(tabel_df), 4):
        cols = st.columns(4)
        batch = tabel_df.iloc[i:i+4]
        
        for index, (idx, row) in enumerate(batch.iterrows()):
            with cols[index]:
                # Her viser vi videoen direkte i kolonnen
                v_fil = video_map.get(row['RENS_ID'])
                video_sti = os.path.join(video_dir, v_fil)
                
                # Overskrift og info over videoen
                st.markdown(f"**{row['SPILLER']}**")
                
                # Selve videoafspilleren
                st.video(video_sti)
                
                # Info under videoen
                st.caption(f"{row['MATCHLABEL']} (xG: {row.get('SHOTXG', 'N/A')})")
                st.markdown("<br>", unsafe_allow_html=True) # Lidt luft til næste række
