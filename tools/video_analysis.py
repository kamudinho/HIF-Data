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
    # --- 1. SETUP & DATA ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path): return

    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(rens_dansk_tekst)
    
    spillere_df = spillere_df.copy()
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['SPILLER'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].map(navne_map).fillna("Ukendt")
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    video_map = { "".join(re.findall(r'\d+', os.path.splitext(f)[0])): f 
                 for f in (os.listdir(video_dir) if os.path.exists(video_dir) else []) if f.lower().endswith('.mp4') }

    final_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    def lav_titel(row):
        event = "Mål" if str(row.get('SHOTISGOAL', '')).lower() in ['true', '1', '1.0', 't', 'yes'] else "Afslutning"
        return f"{event} vs. {row.get('MATCHLABEL', 'Ukendt kamp')}"

    final_df['DYNAMIC_TITLE'] = final_df.apply(lav_titel, axis=1)

    # --- 2. TABEL ---
    event = st.dataframe(
        final_df[["SPILLER", "MATCHLABEL", "SHOTXG", "SHOTBODYPART"]],
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
    )

    # --- 3. MODAL VINDUE ---
    @st.dialog(" ", width="large")
    def vis_analyse(data, v_map, v_dir):
        # Navigation på samme linje som titlen ved hjælp af radio-knap i horisontal mode
        # Vi gemmer den i kolonner for at tvinge den til højre
        col_titel, col_nav = st.columns([3, 1])
        
        with col_titel:
            st.markdown(f"#### {data['DYNAMIC_TITLE']}")
            
        with col_nav:
            # En horisontal radio-knap fungerer som tabs men er mere stabil end knapper
            mode = st.radio("Vælg", ["🎥 Video", "📊 Stats"], label_visibility="collapsed", horizontal=True)

        if mode == "🎥 Video":
            v_fil = v_map.get(data['RENS_ID'])
            video_path = os.path.join(v_dir, v_fil)
            st.video(video_path, autoplay=True)
        else:
            st.write(f"**Spiller:** {data['SPILLER']}")
            m1, m2, m3 = st.columns(3)
            m1.metric("xG", f"{data.get('SHOTXG', 0):.2f}")
            m2.metric("Del", f"{data.get('SHOTBODYPART', 'N/A')}")
            m3.metric("Halvleg", f"{data.get('MATCHPERIOD', 'N/A')}")

    # --- 4. TRIGGER ---
    if len(event.selection.rows) > 0:
        selected_row = final_df.iloc[event.selection.rows[0]]
        vis_analyse(selected_row, video_map, video_dir)
