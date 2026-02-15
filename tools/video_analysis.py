import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # 1. Stier (Relativt til rodmappen hvor HIF-dash.py ligger)
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        st.error(f"Kunne ikke finde matches.csv i {match_path}")
        return

    # 2. Indlæs match-data
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    # 3. Sammenkobling af spillernavne (fra spillere_df sendt fra hovedfilen)
    # Rens ID'er for at sikre match (fjerner .0)
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    
    # Lav navne-map
    if 'NAVN' in spillere_df.columns:
        navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df['NAVN']))
    else:
        # Fallback hvis kolonnen hedder noget andet
        fn = spillere_df.get('FIRSTNAME', '').fillna('')
        ln = spillere_df.get('LASTNAME', '').fillna('')
        spillere_df['FULL_NAME'] = (fn + ' ' + ln).str.strip()
        navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df['FULL_NAME']))

    # Rens ID'er i match-filen
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna(df['PLAYER_WYID'])
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # 4. Find videoer (Fixer .mp4 fejlen ved at splitte endelsen af først)
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                # splitext splitter '123.mp4' -> ('123', '.mp4')
                rent_navn = os.path.splitext(f)[0]
                clean_id = "".join(re.findall(r'\d+', rent_navn))
                video_map[clean_id] = f

    # 5. Filtrer til kun rækker med video
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    # --- FILTER SEKTION ---
    col_a, col_b = st.columns([1, 2])
    with col_a:
        kun_maal = st.toggle("Vis kun mål", value=False)
    
    if kun_maal and 'SHOTISGOAL' in tabel_df.columns:
        # Robust tjek for sand/falsk
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])].copy()

    if tabel_df.empty:
        st.info("Ingen videoer fundet med de valgte kriterier.")
        return

    # 6. MANUEL TABEL MED POPOVERS
    st.markdown("---")
    
    # Overskrifter
    h = st.columns([2, 3, 1, 2])
    h[0].write("**Spiller**")
    h[1].write("**Kamp**")
    h[2].write("**xG**")
    h[3].write("**Video**")
    st.divider()

    # Loop gennem data og tegn rækker
    for idx, row in tabel_df.iterrows():
        c1, c2, c3, c4 = st.columns([2, 3, 1, 2])
        
        c1.write(row['SPILLER'])
        c2.write(row['MATCHLABEL'])
        
        # Vis xG hvis den findes
        xg_val = row.get('SHOTXG', '-')
        c3.write(str(xg_val))
        
        # POPOVER til video - Unik key er vigtig!
        with c4.popover("📽️ Se klip", use_container_width=True):
            vid_id = row['RENS_ID']
            v_fil = video_map.get(vid_id)
            if v_fil:
                st.write(f"**Aktion:** {row['SPILLER']}")
                st.write(f"*{row['MATCHLABEL']}*")
                st.video(os.path.join(video_dir, v_fil))
            else:
                st.error("Videofil ikke fundet")
