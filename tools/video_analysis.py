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
        st.error("Kunne ikke finde matches.csv")
        return

    # --- 2. DATA HENTNING & MAPPING ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Map navne fra spillere_df (ligesom i scouting_db)
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna("Ukendt")
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # Find videoer i mappen
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                vid_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
                video_map[vid_id] = f

    # Filtrer så vi kun viser rækker, hvor der faktisk findes en video
    final_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    # Sidebar filter
    kun_maal = st.sidebar.toggle("Vis kun mål", value=True)
    if kun_maal and 'SHOTISGOAL' in final_df.columns:
        final_df = final_df[final_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', '1.0', 't', 'yes'])]

    # --- 3. HOVEDTABEL (Selection Mode) ---
    # Vi bruger st.dataframe præcis som i din scouting_db
    event = st.dataframe(
        final_df[["SPILLER", "MATCHLABEL", "SHOTXG", "EVENTNAME"]],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        column_config={
            "SPILLER": "Navn",
            "MATCHLABEL": "Kamp",
            "SHOTXG": st.column_config.NumberColumn("xG", format="%.2f"),
            "EVENTNAME": "Type"
        }
    )

    # --- 4. ANALYSE DIALOG (POPUP) ---
    @st.dialog("Videoanalyse & Detaljer", width="large")
    def vis_analyse(data, v_map, v_dir):
        st.markdown(f"### {data['SPILLER']} | {data['MATCHLABEL']}")
        st.divider()

        tab1, tab2 = st.tabs(["🎥 Video", "📊 Situationsbillede"])
        
        with tab1:
            v_fil = v_map.get(data['RENS_ID'])
            video_sti = os.path.join(v_dir, v_fil)
            if os.path.exists(video_sti):
                st.video(video_sti, autoplay=True)
            else:
                st.warning("Videofilen kunne ikke findes.")
            
            st.info(f"**Detaljer:** Event Type: {data.get('EVENTNAME', 'N/A')} | xG: {data.get('SHOTXG', 'N/A')}")

        with tab2:
            # Her kan du loade et specifikt billede (f.svg eller .png) hvis de findes
            # Indtil videre bruger vi et placeholder stadion billede
            st.image("https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1000", 
                     caption="Positionering ved afslutning")
            st.write("**Statistik for aktionen:**")
            col1, col2 = st.columns(2)
            col1.metric("Distance", f"{data.get('SHOTDISTANCE', 'N/A')}m")
            col2.metric("Vinkel", f"{data.get('SHOTANGLE', 'N/A')}°")

    # Tjek om en række er valgt og åbn dialogen
    if len(event.selection.rows) > 0:
        selected_row = final_df.iloc[event.selection.rows[0]]
        vis_analyse(selected_row, video_map, video_dir)
