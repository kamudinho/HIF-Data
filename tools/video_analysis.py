import streamlit as st
import pandas as pd
import os
import re

# --- 1. MODAL / POPUP VINDUE ---
# Dette er funktionen der åbner den store video, når du klikker
@st.dialog("Videoanalyse", width="large")
def vis_video_modal(video_sti, spiller, kamp):
    if os.path.exists(video_sti):
        st.video(video_sti, autoplay=True) # Autoplay sørger for den starter med det samme
        st.subheader(f"{spiller}")
        st.write(f"*{kamp}*")
    else:
        st.error(f"Videofilen kunne ikke findes på stien: {video_sti}")

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # --- 2. KONFIGURATION ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')
    # Standard thumbnail indtil du får dine egne
    thumb_url = "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=500&auto=format&fit=crop"

    if not os.path.exists(match_path):
        st.error("Data mangler: Kunne ikke finde data/matches.csv")
        return

    # --- 3. DATA & MAPPING ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Rens spiller ID'er
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['SPILLER'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].map(navne_map).fillna("Ukendt")
    # Vi bruger EVENT_WYID til at matche filnavnet i /videos
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # --- 4. VIDEO MAPPING ---
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                # Fjerner .mp4 og gemmer ID'et
                vid_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
                video_map[vid_id] = f

    # --- 5. FILTRERING ---
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    
    # Sidebar filter
    kun_maal = st.sidebar.toggle("Vis kun mål", value=True)
    if kun_maal and 'SHOTISGOAL' in tabel_df.columns:
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    # --- 6. DET KLIKBARE GALLERI ---
    # CSS der gør knappen usynlig og billedet klikbart
    st.markdown("""
        <style>
        /* Gør knappen gennemsigtig og placer den over billedet */
        div.stButton > button {
            border: none !important;
            background: transparent !important;
            color: transparent !important;
            width: 100% !important;
            height: 200px !important; /* Matcher ca. billedhøjden */
            position: absolute !important;
            z-index: 10 !important;
        }
        /* Selve containeren for billedet */
        [data-testid="stVerticalBlock"] > div:has(img) {
            position: relative !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if tabel_df.empty:
        st.info("Ingen videoer fundet.")
        return

    for i in range(0, len(tabel_df), 4):
        cols = st.columns(4)
        batch = tabel_df.iloc[i:i+4]
        
        for index, (idx, row) in enumerate(batch.iterrows()):
            with cols[index]:
                v_fil = video_map.get(row['RENS_ID'])
                video_sti = os.path.join(video_dir, v_fil)
                
                # Layout per boks
                st.write(f"**{row['SPILLER']}**")
                
                # 1. Usynlig knap (Dette er selve udløseren)
                if st.button("Play", key=f"btn_{row['RENS_ID']}"):
                    vis_video_modal(video_sti, row['SPILLER'], row['MATCHLABEL'])
                
                # 2. Billedet (Der ligger "under" den usynlige knap)
                st.image(thumb_url, use_container_width=True)
                
                st.caption(row['MATCHLABEL'])
