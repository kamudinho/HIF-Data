import streamlit as st
import pandas as pd
import os
import re

# --- 1. POPUP FUNKTION (FORSTØRRET VIDEO) ---
@st.dialog("Videoanalyse", width="large")
def forstoer_video(video_sti, spiller, kamp, xg):
    st.video(video_sti)
    st.write(f"**Spiller:** {spiller}")
    st.write(f"**Kamp:** {kamp} | **xG:** {xg}")

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # --- 2. OPSÆTNING AF STIER ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        st.error(f"Kunne ikke finde matches.csv")
        return

    # --- 3. DATA-HENTNING OG RENSNING ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    # Map navne fra hovedfilens spillere_df
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna(df['PLAYER_WYID'])
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # --- 4. VIDEO-HENTNING (Fixer .mp4 fejlen) ---
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                filnavn_uden_endelse = os.path.splitext(f)[0]
                clean_id = "".join(re.findall(r'\d+', filnavn_uden_endelse))
                video_map[clean_id] = f

    # --- 5. FILTRERING ---
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    kun_maal = st.sidebar.toggle("Vis kun mål", value=True)
    if kun_maal and 'SHOTISGOAL' in tabel_df.columns:
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    if tabel_df.empty:
        st.info("Ingen videoer fundet.")
        return

    # --- 6. VISNING I GRID (4 PR. RÆKKE) ---
    st.write(f"Viser {len(tabel_df)} mål. Klik på 'Forstør' for at se i stort format.")
    
    for i in range(0, len(tabel_df), 4):
        cols = st.columns(4)
        batch = tabel_df.iloc[i:i+4]
        
        for index, (idx, row) in enumerate(batch.iterrows()):
            with cols[index]:
                v_fil = video_map.get(row['RENS_ID'])
                video_sti = os.path.join(video_dir, v_fil)
                
                # Vis en lille video som thumbnail
                st.markdown(f"**{row['SPILLER']}**")
                st.video(video_sti) # Denne kan stadig spilles i lille format
                
                # Forstør-knap der trigger @st.dialog
                xg_text = row.get('SHOTXG', 'N/A')
                if st.button(f"🔎 Forstør", key=f"btn_{row['RENS_ID']}_{idx}", use_container_width=True):
                    forstoer_video(video_sti, row['SPILLER'], row['MATCHLABEL'], xg_text)
                
                st.caption(f"{row['MATCHLABEL']}")
                st.markdown("<br>", unsafe_allow_html=True)
