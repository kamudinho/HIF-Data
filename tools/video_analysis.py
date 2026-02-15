import streamlit as st
import pandas as pd
import os
import re

# --- 1. POPUP DIALOG (Denne åbner når du klikker på billedet) ---
@st.dialog("Videoanalyse", width="large")
def vis_video_modal(video_sti, spiller, kamp):
    st.video(video_sti)
    st.subheader(f"{spiller}")
    st.write(f"*{kamp}*")

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # --- 2. KONFIGURATION ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')
    thumb_url = "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=500&auto=format&fit=crop"

    if not os.path.exists(match_path):
        st.error("Data mangler")
        return

    # --- 3. DATA & MAPPING ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['SPILLER'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].map(navne_map).fillna("Ukendt")
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # --- 4. VIDEO MAPPING ---
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                vid_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
                video_map[vid_id] = f

    # --- 5. FILTRERING ---
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    kun_maal = st.sidebar.toggle("Vis kun mål", value=True)
    if kun_maal:
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    # --- 6. DET KLIKBARE GALLERI ---
    # Dette CSS fjerner alt udseende fra knappen, så kun indholdet (billedet) er synligt
    st.markdown("""
        <style>
        button[kind="secondary"] {
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
            width: 100% !important;
            height: auto !important;
        }
        button[kind="secondary"]:hover {
            opacity: 0.8;
            transform: scale(1.01);
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
                
                # Vi bruger en knap uden tekst, men indsætter et billede over den
                # Når man trykker på "knappen" (billedområdet), åbner dialogen
                st.write(f"**{row['SPILLER']}**")
                
                # Vi laver selve billedet klikbart ved at lægge det ind i en knap-container
                if st.button("", key=f"img_btn_{row['RENS_ID']}"):
                    vis_video_modal(video_sti, row['SPILLER'], row['MATCHLABEL'])
                
                # Vi viser billedet lige under/i knappen. 
                # Fordi CSS'en gør knappen usynlig, vil det føles som om man trykker på billedet.
                st.image(thumb_url, use_column_width=True)
                st.caption(row['MATCHLABEL'])
