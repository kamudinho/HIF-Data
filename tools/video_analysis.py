import streamlit as st
import pandas as pd
import os
import re

# --- 1. POPUP DIALOG (FORSTØRRET VIDEO) ---
@st.dialog("Videoanalyse", width="large")
def forstoer_video(video_sti, spiller, kamp, xg):
    st.video(video_sti)
    st.write(f"### {spiller}")
    st.write(f"**Kamp:** {kamp} | **xG:** {xg}")
    st.button("Luk", on_click=st.rerun)

def vis_side(spillere_df):
    st.title("HIF Videoanalyse")
    
    # --- 2. KONFIGURATION ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')
    # Standard placeholder hvis thumbnail mangler
    thumb_placeholder = "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=500&auto=format&fit=crop"

    if not os.path.exists(match_path):
        st.error("Kunne ikke finde matches.csv")
        return

    # --- 3. DATA HENTNING ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna(df['PLAYER_WYID'])
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # --- 4. VIDEO MAPPING ---
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                rent_navn = os.path.splitext(f)[0]
                clean_id = "".join(re.findall(r'\d+', rent_navn))
                video_map[clean_id] = f

    # --- 5. FILTRERING ---
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()
    kun_maal = st.sidebar.toggle("Vis kun mål", value=True)
    if kun_maal and 'SHOTISGOAL' in tabel_df.columns:
        tabel_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    if tabel_df.empty:
        st.info("Ingen klip fundet.")
        return

    # --- 6. GRID VISNING (4 PR. RÆKKE) ---
    # Vi bruger custom CSS til at gøre knappen usynlig/integreret med billedet
    st.markdown("""
        <style>
        div.stButton > button {
            height: auto;
            padding-top: 10px !important;
            padding-bottom: 10px !important;
            background-color: #f0f2f6;
            border: 1px solid #ddd;
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
                xg_val = row.get('SHOTXG', 'N/A')

                # VIS BILLEDET SOM "THUMBNAIL"
                st.image(thumb_placeholder, use_column_width=True)
                
                # KNAPPEN LIGE UNDER BILLEDET (Fungerer som udløser)
                # Vi giver den spillerens navn og kampen som tekst
                if st.button(f"▶️ {row['SPILLER']}\n{row['MATCHLABEL']}", key=f"play_{row['RENS_ID']}_{idx}", use_container_width=True):
                    forstoer_video(video_sti, row['SPILLER'], row['MATCHLABEL'], xg_val)
                
                st.markdown("<br>", unsafe_allow_html=True)
