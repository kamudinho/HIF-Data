import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_indput):
    st.title("HIF Analyse-dashboard")
    
    # 1. Konfiguration af stier
    csv_path = 'data/matches.csv'
    players_path = 'data/players.csv'
    video_dir = 'videos'

    # Tjek om match-data eksisterer
    if not os.path.exists(csv_path):
        st.error(f"Kunne ikke finde datafilen: {csv_path}")
        return

    # 2. Indlæs kampsdata
    df = pd.read_csv(csv_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    # 3. Indlæs og map spillernavne (players.csv)
    navne_map = {}
    if os.path.exists(players_path):
        p_df = pd.read_csv(players_path, encoding='utf-8-sig', sep=None, engine='python')
        p_df.columns = [c.strip().upper() for c in p_df.columns]
        
        # Sørg for at vi har en NAVN kolonne (kombiner for- og efternavn hvis nødvendigt)
        if 'NAVN' not in p_df.columns and 'FIRSTNAME' in p_df.columns:
            p_df['NAVN'] = p_df['FIRSTNAME'].fillna('') + ' ' + p_df['LASTNAME'].fillna('')
        
        # Rens PLAYER_WYID for at undgå .0 decimaler
        p_df['PLAYER_WYID_CLEAN'] = p_df['PLAYER_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))
        navne_map = dict(zip(p_df['PLAYER_WYID_CLEAN'], p_df['NAVN']))

    # 4. Rens hændelses-ID'er og spiller-ID'er i hoved-data
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))
    
    # Tilføj spillernavn som en kolonne
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna(df['PLAYER_WYID'])

    # 5. Find videoer (VIGTIGT: Fjern .mp4 før rensning for tal)
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                # splitext splitter '158304714.mp4' til ('158304714', '.mp4')
                filnavn_uden_endelse = os.path.splitext(f)[0]
                
                # Nu fjerner vi kun tal fra selve navnet (så vi ikke snupper 4-tallet fra .mp4)
                clean_id = "".join(re.findall(r'\d+', filnavn_uden_endelse))
                video_map[clean_id] = f

    # 6. Filtrer data så vi kun viser rækker, hvor der findes en video
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    if tabel_df.empty:
        st.warning("Ingen matchende videoer fundet i mappen.")
        # Lille hjælp til fejlfinding
        if st.checkbox("Vis teknisk info (Hvorfor virker det ikke?)"):
            st.write(f"Antal filer i /videos: {len(os.listdir(video_dir)) if os.path.exists(video_dir) else 0}")
            st.write("Første 5 ID'er i din CSV:", df['RENS_ID'].head().tolist())
        return

    # 7. Visning af den "helt almindelige" tabel
    st.subheader("Alle sekvenser med video")
    
    # Vælg de kolonner vi vil vise
    vis_cols = ['EVENT_WYID', 'SPILLER', 'MATCHLABEL', 'SHOTBODYPART', 'SHOTISGOAL', 'SHOTXG', 'DATE', 'VENUE']
    
    st.dataframe(
        tabel_df[vis_cols],
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

    # 8. Vælg video via ID
    st.write("---")
    valgt_event = st.selectbox(
        "Vælg et ID fra tabellen for at se video:", 
        options=tabel_df['EVENT_WYID'].unique(),
        format_func=lambda x: str(x).replace(',', '').replace('.', '') # Fjerner tusindtalsseparatorer i visning
    )

    if valgt_event:
        sid = "".join(re.findall(r'\d+', str(valgt_event).split('.')[0]))
        if sid in video_map:
            st.write(f"Afspiller video for: {tabel_df[tabel_df['EVENT_WYID']==valgt_event]['SPILLER'].values[0]}")
            st.video(os.path.join(video_dir, video_map[sid]))
