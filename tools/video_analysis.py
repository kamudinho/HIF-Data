import streamlit as st
import pandas as pd
import os
import re

# --- 1. DIALOG TIL FORSTØRRET VISNING ---
@st.dialog("Videoanalyse - Stor skærm", width="large")
def vis_stort_format(video_sti, spiller, info, key_to_reset):
    st.video(video_sti, autoplay=True)
    st.subheader(spiller)
    st.write(info)
    # Når brugeren klikker på "Luk" eller udenfor boksen i Streamlit, 
    # skal vi sikre os at siden genindlæses for at nulstille checkboxen.
    if st.button("Luk og nulstil"):
        st.session_state[key_to_reset] = False
        st.rerun()

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # --- 2. DATA & STIER ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        st.error("Data mangler: Kunne ikke finde data/matches.csv")
        return

    # Indlæs data
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Map navne
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

    if tabel_df.empty:
        st.info("Ingen videoer fundet.")
        return

    # --- 3. TABEL-LAYOUT ---
    st.markdown("---")
    # Vi bruger [3, 4, 1, 2] for at få en mindre video-kolonne til højre
    h_col1, h_col2, h_col3, h_col4 = st.columns([3, 4, 1, 2])
    h_col1.write("**Spiller**")
    h_col2.write("**Kamp**")
    h_col3.write("**xG**")
    h_col4.write("**Video**")
    st.divider()

    for idx, row in tabel_df.iterrows():
        c1, c2, c3, c4 = st.columns([3, 4, 1, 2])
        
        c1.write(f"**{row['SPILLER']}**")
        c2.write(row['MATCHLABEL'])
        c3.write(str(row.get('SHOTXG', '-')))
        
        with c4:
            v_fil = video_map.get(row['RENS_ID'])
            video_sti = os.path.join(video_dir, v_fil)
            
            # Lille preview video
            st.video(video_sti)
            
            # Checkbox logik med automatisk reset
            cb_key = f"chk_{row['RENS_ID']}_{idx}"
            
            # Initialiser session_state hvis den ikke findes
            if cb_key not in st.session_state:
                st.session_state[cb_key] = False
                
            # Tegn checkboxen baseret på session_state
            forstoer = st.checkbox("Forstør", key=cb_key)
            
            if forstoer:
                vis_stort_format(video_sti, row['SPILLER'], row['MATCHLABEL'], cb_key)
        
        st.divider()
