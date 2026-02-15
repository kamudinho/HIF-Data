import streamlit as st
import pandas as pd
import os
import re

def rens_dansk_tekst(tekst):
    if not isinstance(tekst, str): return tekst
    fejl_map = {"√∏": "ø", "√¶": "æ", "√•": "å", "√ò": "Ø", "√Ü": "Æ", "√Ö": "Å"}
    for fejl, ret in fejl_map.items():
        tekst = tekst.replace(fejl, ret)
    return tekst

def vis_side(spillere_df):
    # --- 1. SETUP ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        st.error("Kunne ikke finde matches.csv")
        return

    # --- 2. DATA ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Rens teksten med det samme
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(rens_dansk_tekst)
    
    spillere_df = spillere_df.copy()
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['SPILLER'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].map(navne_map).fillna("Ukendt")
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # Mapping af videoer
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                vid_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
                video_map[vid_id] = f

    final_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    # --- 3. TABEL ---
    # Vi viser kun de mest nødvendige kolonner for at undgå fejl
    vis_kolonner = ["SPILLER", "MATCHLABEL", "SHOTXG", "SHOTBODYPART"]
    eksisterende = [k for k in vis_kolonner if k in final_df.columns]
    
    event = st.dataframe(
        final_df[eksisterende],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row"
    )

    # --- 4. MODAL VINDUE ---
    # Vi bruger en fast titel her for at sikre stabilitet
    @st.dialog("Video")
    def vis_analyse(row_data, v_map, v_dir):
        # Dynamisk undertitel inde i dialogen
        is_goal = str(row_data.get('SHOTISGOAL', '')).lower() in ['true', '1', '1.0', 't', 'yes']
        label = "Mål" if is_goal else "Afslutning"
        match = row_data.get('MATCHLABEL', 'Kamp')
        
        st.write(f"### {label} vs. {match}")
        
        t1, t2 = st.tabs(["Video", "Statistik"])
        
        with t1:
            v_fil = v_map.get(row_data['RENS_ID'])
            if v_fil:
                st.video(os.path.join(v_dir, v_fil), autoplay=True)
            else:
                st.warning("Videofilen blev ikke fundet.")

        with t2:
            st.write(f"**Spiller:** {row_data['SPILLER']}")
            c1, c2 = st.columns(2)
            c1.metric("xG", f"{row_data.get('SHOTXG', 0):.2f}")
            c2.metric("Halvleg", f"{row_data.get('MATCHPERIOD', 'N/A')}")

    # --- 5. TRIGGER ---
    if len(event.selection.rows) > 0:
        index = event.selection.rows[0]
        selected_row = final_df.iloc[index]
        vis_analyse(selected_row, video_map, video_dir)
