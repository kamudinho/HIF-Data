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
        st.error(f"Kunne ikke finde matches.csv")
        return

    # --- 2. DATA HENTNING ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Map navne
    spillere_df = spillere_df.copy()
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna("Ukendt")
    
    if 'EVENT_WYID' in df.columns:
        df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))
    else:
        st.error("Kolonnen 'EVENT_WYID' mangler")
        return

    # --- 3. VIDEO MAPPING ---
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                vid_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
                video_map[vid_id] = f

    # Filtrer data til kun rækker med video
    final_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    # --- 4. DYNAMISK TITEL LOGIK ---
    # Vi laver en hjælpe-kolonne til visning i popup
    def lav_titel(row):
        event = "Mål" if str(row.get('SHOTISGOAL', '')).lower() in ['true', '1', '1.0', 't', 'yes'] else "Afslutning"
        match = row.get('MATCHLABEL', 'Ukendt kamp')
        return f"{event} vs. {match}"

    final_df['VIDEO_TITEL'] = final_df.apply(lav_titel, axis=1)

    # --- 5. HOVEDTABEL ---
    # Vi definerer de kolonner vi gerne vil have med (hvis de findes)
    kolonne_map = {
        "SPILLER": "Navn",
        "MATCHLABEL": "Kamp",
        "TEAMNAME": "Hold",
        "PERIOD": "Halvleg",
        "EVENTSEC": "Sekund",
        "SHOTXG": "xG",
        "EVENTNAME": "Type"
    }
    
    eksisterende = [k for k in kolonne_map.keys() if k in final_df.columns]
    
    event = st.dataframe(
        final_df[eksisterende],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        column_config={
            "SHOTXG": st.column_config.NumberColumn("xG", format="%.2f"),
            "EVENTSEC": st.column_config.NumberColumn("Sekund", format="%d"),
            "PERIOD": "H",
            "TEAMNAME": "Hold"
        }
    )

    # --- 6. ANALYSE DIALOG (POPUP) ---
    @st.dialog("Videoanalyse", width="large")
    def vis_analyse(data, v_map, v_dir):
        # Her bruger vi din nye ønskede overskrift
        st.markdown(f"### {data['VIDEO_TITEL']}")
        st.markdown(f"**Spiller:** {data['SPILLER']}")
        st.divider()

        tab1, tab2 = st.tabs(["🎥 Video", "📊 Detaljer"])
        
        with tab1:
            v_fil = v_map.get(data['RENS_ID'])
            video_sti = os.path.join(v_dir, v_fil)
            st.video(video_sti, autoplay=True)

        with tab2:
            st.write("**Information om aktionen:**")
            c1, c2, c3 = st.columns(3)
            if 'SHOTXG' in data: c1.metric("xG", f"{data['SHOTXG']:.2f}")
            if 'PERIOD' in data: c2.metric("Halvleg", f"{data['PERIOD']}")
            if 'EVENTSEC' in data: c3.metric("Tid (sek)", f"{int(data['EVENTSEC'])}")
            
            st.write("---")
            st.write(f"**Hold:** {data.get('TEAMNAME', 'N/A')}")
            st.write(f"**Event:** {data.get('EVENTNAME', 'N/A')}")

    # Vis dialog hvis række vælges
    if len(event.selection.rows) > 0:
        selected_row = final_df.iloc[event.selection.rows[0]]
        vis_analyse(selected_row, video_map, video_dir)
