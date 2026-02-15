import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere_df):
    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 20px;'>HIF Videoanalyse</p>", unsafe_allow_html=True)
    
    # --- 1. OPSÆTNING AF STIER ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        st.error(f"Kunne ikke finde matches.csv på stien: {match_path}")
        return

    # --- 2. DATA HENTNING ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    # Rens kolonnenavne (fjern mellemrum og gør dem store)
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Map navne fra spillere_df
    spillere_df = spillere_df.copy()
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna("Ukendt")
    
    # RENS_ID til video-match
    if 'EVENT_WYID' in df.columns:
        df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))
    else:
        st.error("Kolonnen 'EVENT_WYID' mangler i matches.csv")
        return

    # --- 3. VIDEO MAPPING ---
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                vid_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
                video_map[vid_id] = f

    # Filtrer data
    final_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    if final_df.empty:
        st.info("Ingen videoer fundet i mappen /videos, der matcher data i matches.csv")
        return

    # --- 4. DYNAMISK KOLONNEVALG (Sikrer mod KeyError) ---
    # Vi tjekker hvilke kolonner der rent faktisk findes i din CSV
    mulige_kolonner = {
        "SPILLER": "Navn",
        "MATCHLABEL": "Kamp",
        "SHOTXG": "xG",
        "EVENTNAME": "Type",
        "SUBEVENTNAME": "Detalje"
    }
    
    # Find kun de kolonner der findes i CSV'en
    eksisterende_kolonner = [k for k in mulige_kolonner.keys() if k in final_df.columns]
    
    # --- 5. HOVEDTABEL ---
    event = st.dataframe(
        final_df[eksisterende_kolonner],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        column_config={k: mulige_kolonner[k] for k in eksisterende_kolonner if k == "SHOTXG"} # Formatér kun xG hvis den findes
    )

    # --- 6. ANALYSE DIALOG ---
    @st.dialog("Videoanalyse", width="large")
    def vis_analyse(data, v_map, v_dir):
        st.markdown(f"### {data['SPILLER']}")
        if 'MATCHLABEL' in data: st.write(f"**Kamp:** {data['MATCHLABEL']}")
        st.divider()

        tab1, tab2 = st.tabs(["🎥 Video", "📊 Detaljer"])
        
        with tab1:
            v_fil = v_map.get(data['RENS_ID'])
            video_sti = os.path.join(v_dir, v_fil)
            st.video(video_sti, autoplay=True)

        with tab2:
            st.write("Statistik for denne aktion:")
            col1, col2 = st.columns(2)
            if 'SHOTXG' in data: col1.metric("xG", f"{data['SHOTXG']:.2f}")
            if 'EVENTNAME' in data: col2.write(f"**Type:** {data['EVENTNAME']}")

    # Vis profil hvis række vælges
    if len(event.selection.rows) > 0:
        selected_row = final_df.iloc[event.selection.rows[0]]
        vis_analyse(selected_row, video_map, video_dir)
