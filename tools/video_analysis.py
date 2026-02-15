import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # 1. Konfiguration
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')
    # Placeholder billede hvis du ikke har thumbnails
    placeholder_url = "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=500&auto=format&fit=crop"

    if not os.path.exists(match_path):
        st.error("Kunne ikke finde matches.csv")
        return

    # 2. Indlæs og forbered data
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    # Map navne
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna("Ukendt Spiller")
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # 3. Find videoer
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                rent_navn = os.path.splitext(f)[0]
                clean_id = "".join(re.findall(r'\d+', rent_navn))
                video_map[clean_id] = f

    # 4. Filtrer data
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    # Toggle for kun mål
    kun_maal = st.sidebar.toggle("Vis kun mål", value=True)
    if kun_maal and 'SHOTISGOAL' in tabel_df.columns:
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    if tabel_df.empty:
        st.info("Ingen videoer fundet.")
        return

    # --- 5. GRID VISNING (4 PR. RÆKKE) ---
    st.write(f"Viser {len(tabel_df)} sekvenser")
    
    # Vi bruger et loop til at lave rækker med 4 kolonner i hver
    for i in range(0, len(tabel_df), 4):
        cols = st.columns(4)
        # Hent de næste 4 rækker fra data
        batch = tabel_df.iloc[i:i+4]
        
        for index, (idx, row) in enumerate(batch.iterrows()):
            with cols[index]:
                # Vi lægger popoveren "ovenpå" billedet
                with st.popover(f"🎥 {row['SPILLER']}", use_container_width=True):
                    v_fil = video_map.get(row['RENS_ID'])
                    st.write(f"**{row['MATCHLABEL']}**")
                    st.video(os.path.join(video_dir, v_fil))
                
                # Miniaturebillede
                st.image(placeholder_url, use_column_width=True, caption=f"{row['MATCHLABEL']}")
                st.caption(f"xG: {row.get('SHOTXG', 'N/A')}")
                st.markdown("---")
