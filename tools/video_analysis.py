import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        st.error(f"Fil mangler: {match_path}")
        return

    # 1. Indlæs
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    # 2. Map Navne (Robust)
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', spillere_df.get('FIRSTNAME', 'Ukendt'))))

    # 3. Rens ID'er
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))
    df['SPILLER'] = df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False).map(navne_map).fillna("Ukendt")

    # 4. Video Map
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                rent_navn = os.path.splitext(f)[0]
                vid_id = "".join(re.findall(r'\d+', rent_navn))
                video_map[vid_id] = f

    # 5. Filtrer til videoer der findes
    data_med_video = df[df['RENS_ID'].isin(video_map.keys())].copy()

    # --- DEBUG INFO ---
    st.sidebar.write(f"Videoer i mappe: {len(video_map)}")
    st.sidebar.write(f"Rækker med video-match: {len(data_med_video)}")

    # Toggle filter
    kun_maal = st.toggle("Vis kun mål", value=False) # Start med False for at se om det virker
    
    if kun_maal:
        data_med_video = data_med_video[data_med_video['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])].copy()

    if data_med_video.empty:
        st.warning("Ingen rækker at vise. Prøv at slå 'Vis kun mål' fra.")
    else:
        # 6. TEGN TABELLEN MANUELT
        # Vi laver overskrifter
        h = st.columns([2, 3, 1, 2])
        h[0].write("**Spiller**")
        h[1].write("**Kamp**")
        h[2].write("**xG**")
        h[3].write("**Video**")
        st.divider()

        # Loop igennem rækkerne
        for idx, row in data_med_video.iterrows():
            c1, c2, c3, c4 = st.columns([2, 3, 1, 2])
            
            c1.write(row['SPILLER'])
            c2.write(row['MATCHLABEL'])
            c3.write(str(row.get('SHOTXG', '-')))
            
            # POP-OVER MED UNIK KEY
            # Vi kombinerer index og ID for at være 100% sikre på unikhed
            with c4.popover("Se video", key=f"pop_{idx}_{row['RENS_ID']}", use_container_width=True):
                v_fil = video_map.get(row['RENS_ID'])
                if v_fil:
                    st.video(os.path.join(video_dir, v_fil))
                else:
                    st.write("Video ikke fundet")
