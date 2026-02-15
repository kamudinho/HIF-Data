import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # 1. Konfiguration af stier (Husk at 'data' mappen skal findes)
    # Da din app kører fra rod-mappen, skal vi pege rigtigt på filerne
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    # 2. Tjek om matches.csv findes
    if not os.path.exists(match_path):
        st.error(f"Kunne ikke finde datafilen: {match_path}")
        # Debug hjælp: viser hvad der faktisk findes i data-mappen
        data_folder = os.path.join(BASE_DIR, 'data')
        if os.path.exists(data_folder):
            st.write("Filer i data-mappen:", os.listdir(data_folder))
        return

    # 3. Indlæs match-data (skud/begivenheder)
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    # 4. Sammenkobling med spillernavne (fra spillere_df sendt fra hovedfilen)
    # Vi sikrer os at PLAYER_WYID er tekst uden .0
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    
    # Lav opslagsværket (Map ID -> Navn)
    # Vi bruger 'NAVN' eller kombinerer 'FIRSTNAME'/'LASTNAME'
    if 'NAVN' in spillere_df.columns:
        navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df['NAVN']))
    else:
        spillere_df['FULL_NAME'] = spillere_df['FIRSTNAME'].fillna('') + ' ' + spillere_df['LASTNAME'].fillna('')
        navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df['FULL_NAME']))

    # Rens ID'er i match-data
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna(df['PLAYER_WYID'])
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # 5. Find videoer (Fixer .mp4 fejlen ved at fjerne endelsen før rensning)
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                rent_navn = os.path.splitext(f)[0] # Fjerner .mp4
                clean_id = "".join(re.findall(r'\d+', rent_navn)) # Finder ID
                video_map[clean_id] = f

    # 6. Filtrer til kun rækker med video
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    if tabel_df.empty:
        st.warning("Ingen matchende videoer fundet i mappen 'videos/'.")
        return

    # 7. Visning
    st.subheader("Sæsonens mål & aktioner")
    
    # Vis tabel
    vis_cols = ['EVENT_WYID', 'SPILLER', 'MATCHLABEL', 'SHOTISGOAL', 'SHOTXG', 'SCORE']
    # Vi filtrerer kolonnerne så vi kun viser dem der faktisk findes
    findes_cols = [c for c in vis_cols if c in tabel_df.columns]
    
    st.dataframe(tabel_df[findes_cols], use_container_width=True, hide_index=True)

    # 8. Video-vælger
    st.write("---")
    valgt_event = st.selectbox(
        "Vælg en aktion for at se video", 
        options=tabel_df['EVENT_WYID'].unique(),
        format_func=lambda x: f"ID: {str(x).split('.')[0]}"
    )

    if valgt_event:
        sid = "".join(re.findall(r'\d+', str(valgt_event).split('.')[0]))
        if sid in video_map:
            video_sti = os.path.join(video_dir, video_map[sid])
            st.video(video_sti)
