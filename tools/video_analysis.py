import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # 1. Stier og Placeholder
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')
    # Flot stadion placeholder
    thumb_url = "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=500&auto=format&fit=crop"

    if not os.path.exists(match_path):
        st.error("Data mangler")
        return

    # 2. Data og Mapping (Samme stærke logik som før)
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    df['SPILLER'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].map(navne_map)
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # 3. Video Mapping
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                vid_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
                video_map[vid_id] = f

    # 4. Filtrering
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    kun_maal = st.sidebar.toggle("Vis kun mål", value=True)
    if kun_maal:
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    if tabel_df.empty:
        st.info("Ingen klip fundet.")
        return

    # --- 5. GRID MED BILLED-POPUP ---
    # CSS for at få popover-knappen til at ligne et galleri-kort
    st.markdown("""
        <style>
        div[data-testid="stPopover"] > button {
            border: none !important;
            padding: 0px !important;
            background-color: transparent !important;
            width: 100% !important;
        }
        div[data-testid="stPopover"] > button:hover {
            transform: scale(1.02);
            transition: 0.2s;
        }
        </style>
    """, unsafe_allow_html=True)

    for i in range(0, len(tabel_df), 4):
        cols = st.columns(4)
        batch = tabel_df.iloc[i:i+4]
        
        for index, (idx, row) in enumerate(batch.iterrows()):
            with cols[index]:
                v_fil = video_map.get(row['RENS_ID'])
                video_sti = os.path.join(video_dir, v_fil)

                # Vi bruger popoveren som selve "kortet"
                # Teksten i label bliver spillerens navn
                with st.popover(f"🎥 {row['SPILLER']}", use_container_width=True):
                    # Indeni popoveren viser vi den store video
                    st.video(video_sti)
                    st.write(f"**{row['MATCHLABEL']}**")
                    st.write(f"xG: {row.get('SHOTXG', 'N/A')}")

                # Lige under popover-knappen viser vi billedet
                st.image(thumb_url, use_column_width=True)
                st.caption(f"{row['MATCHLABEL']}")
