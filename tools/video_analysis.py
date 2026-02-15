import streamlit as st
import pandas as pd
import os
import re

def rens_dansk_tekst(tekst):
    if not isinstance(tekst, str): return tekst
    # Kombineret map så intet bliver overskrevet
    fejl_map = {
        "√∏": "ø", "√¶": "æ", "√•": "å", 
        "√ò": "Ø", "√Ü": "Æ", "√Ö": "Å",
        "left_foot": "Venstre fod", 
        "right_foot": "Højre fod"
    }
    for fejl, ret in fejl_map.items():
        tekst = tekst.replace(fejl, ret)
    return tekst

def vis_side(spillere_df):
    # --- 1. DATA & SETUP ---
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
        is_goal = str(row.get('SHOTISGOAL', '')).lower() in ['true', '1', '1.0', 't', 'yes']
        event = "Mål" if is_goal else "Afslutning"
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
        # CSS HACK: Gør knapperne til ren tekst
        st.markdown("""
            <style>
                div[data-testid="stColumn"] button {
                    border: none !important;
                    background-color: transparent !important;
                    color: inherit !important;
                    padding: 0px !important;
                    text-decoration: underline;
                }
                div[data-testid="stColumn"] button:hover {
                    color: #ff4b4b !important;
                    text-decoration: none;
                }
            </style>
        """, unsafe_allow_html=True)

        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "Video"

        head_col, btn_col1, btn_col2 = st.columns([6, 1.2, 1.2])
        
        with head_col:
            st.subheader(data['DYNAMIC_TITLE'])
        
        with btn_col1:
            if st.button("Video"):
                st.session_state.active_tab = "Video"
                st.rerun()
        
        with btn_col2:
            if st.button("Stats"):
                st.session_state.active_tab = "Stats"
                st.rerun()

        if st.session_state.active_tab == "Video":
            v_fil = v_map.get(data['RENS_ID'])
            st.video(os.path.join(v_dir, v_fil), autoplay=True)
        else:
            st.write(f"**Spiller:** {data['SPILLER']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("xG", f"{data.get('SHOTXG', 0):.2f}")
            c2.metric("Del", f"{data.get('SHOTBODYPART', 'N/A')}")
            c3.metric("Halvleg", f"{data.get('MATCHPERIOD', 'N/A')}")

    if len(event.selection.rows) > 0:
        vis_analyse(final_df.iloc[event.selection.rows[0]], video_map, video_dir)
