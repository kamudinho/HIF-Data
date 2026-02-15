import streamlit as st
import pandas as pd
import os
import re

def rens_dansk_tekst(tekst):
    """Retter fejl i tegnkodning for danske bogstaver."""
    if not isinstance(tekst, str):
        return tekst
    fejl_map = {
        "√∏": "ø", "√¶": "æ", "√•": "å",
        "√ò": "Ø", "√Ü": "Æ", "√Ö": "Å"
    }
    for fejl, ret in fejl_map.items():
        tekst = tekst.replace(fejl, ret)
    return tekst

def vis_side(spillere_df):
    # --- 1. OPSÆTNING ---
    BASE_DIR = os.getcwd()
    match_path = os.path.join(BASE_DIR, 'data', 'matches.csv')
    video_dir = os.path.join(BASE_DIR, 'videos')

    if not os.path.exists(match_path):
        return

    # --- 2. DATA ---
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(rens_dansk_tekst)
    
    spillere_df = spillere_df.copy()
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_map = dict(zip(spillere_df['PLAYER_WYID'], spillere_df.get('NAVN', 'Ukendt')))
    
    df['PLAYER_RENS'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['SPILLER'] = df['PLAYER_RENS'].map(navne_map).fillna("Ukendt")
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))

    # --- 3. VIDEO MAPPING ---
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                vid_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
                video_map[vid_id] = f

    final_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    def lav_titel(row):
        is_goal = str(row.get('SHOTISGOAL', '')).lower() in ['true', '1', '1.0', 't', 'yes']
        event = "Mål" if is_goal else "Afslutning"
        return f"{event} vs. {row.get('MATCHLABEL', 'Ukendt kamp')}"

    final_df['DYNAMIC_TITLE'] = final_df.apply(lav_titel, axis=1)

    # --- 4. TABEL ---
    event = st.dataframe(
        final_df[["SPILLER", "MATCHLABEL", "SHOTXG", "SHOTBODYPART"]],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row"
    )

    # --- 5. MODAL VINDUE (OPTIMERET PLADS) ---
    @st.dialog(" ", width="large")
    def vis_analyse(data, v_map, v_dir):
        # CSS hack: Fjerner polstring i dialog-boksen så videoen kan blive større
        st.markdown("""
            <style>
                [data-testid="stDialog"] div:first-child { padding: 10px; }
                .stTabs [data-baseweb="tab-panel"] { padding-top: 10px; }
            </style>
        """, unsafe_allow_html=True)

        st.subheader(data['DYNAMIC_TITLE'])
        
        tab1, tab2 = st.tabs(["🎥 Video", "📊 Statistik"])
        
        with tab1:
            v_fil = v_map.get(data['RENS_ID'])
            video_sti = os.path.join(v_dir, v_fil)
            # Vi sikrer os at videoen bruger 100% bredde
            st.video(video_sti, autoplay=True)

        with tab2:
            st.write(f"**Spiller:** {data['SPILLER']}")
            c1, c2, c3 = st.columns(3)
            if 'SHOTXG' in data: c1.metric("xG", f"{data['SHOTXG']:.2f}")
            if 'SHOTBODYPART' in data: c2.metric("Del", f"{data['SHOTBODYPART']}")
            if 'MATCHPERIOD' in data: c3.metric("Halvleg", f"{data['MATCHPERIOD']}")

    # --- 6. TRIGGER ---
    if len(event.selection.rows) > 0:
        selected_row = final_df.iloc[event.selection.rows[0]]
        vis_analyse(selected_row, video_map, video_dir)
