import streamlit as st
import pandas as pd
import os
import re

# 1. Popup-vindue (Modal)
@st.dialog("Videoanalyse")
def vis_video_popup(data, filnavn, video_dir):
    st.subheader(f"{data.get('MATCHLABEL', 'Kamp-data')}")
    
    if filnavn:
        st.video(os.path.join(video_dir, filnavn))
    else:
        st.warning("Videofilen kunne ikke findes.")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Kropsdel:** {data.get('SHOTBODYPART', 'N/A')}")
        st.write(f"**Bane:** {data.get('VENUE', 'N/A')}")
        st.write(f"🆔 **ID:** {data.get('EVENT_WYID', 'N/A')}")
    with col2:
        er_maal = str(data.get('SHOTISGOAL', 'false')).lower() == 'true'
        st.write(f"**Mål:** {'✅ JA' if er_maal else '❌ NEJ'}")
        st.metric("xG Værdi", f"{data.get('SHOTXG', '0.00')}")
        st.write(f"📅 **Dato:** {data.get('DATE', 'N/A')}")

# 2. Hovedfunktionen
def vis_side(spillere):
    st.title("⚽ HIF Analyse-dashboard")
    
    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error(f"Kunne ikke finde filen: {csv_path}")
        return

    # Indlæs og rens
    df = pd.read_csv(csv_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Rens ID'er til video-match
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x)))

    # Find videoer i mappen
    video_map = {}
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        for f in video_filer:
            clean_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
            video_map[clean_id] = f

    # Vis kun rækker, hvor der findes en video
    video_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    if video_df.empty:
        st.info("Ingen matchende videoer fundet i mappen.")
        return

    # TABEL-HEADER (Uden border)
    h_cols = st.columns([0.6, 2, 1, 0.8, 0.8, 1, 1.5])
    headers = ["Video", "Kamp", "Kropsdel", "Mål", "xG", "Bane", "Dato"]
    for col, text in zip(h_cols, headers):
        col.markdown(f"**{text}**")

    # DATA-RÆKKER (Med border)
    for idx, row in video_df.iterrows():
        # border=True skaber den ramme du efterspørger omkring hver række
        with st.container(border=True):
            c = st.columns([0.6, 2, 1, 0.8, 0.8, 1, 1.5])
            
            # 1. Video knap (EVENT_WYID bruges som key)
            if c[0].button("▶️", key=f"btn_{row['RENS_ID']}"):
                vis_video_popup(row, video_map.get(row['RENS_ID']), video_dir)
            
            # 2. MATCHLABEL
            c[1].write(row.get('MATCHLABEL', 'N/A'))
            
            # 3. SHOTBODYPART
            c[2].write(row.get('SHOTBODYPART', 'N/A'))
            
            # 4. SHOTISGOAL (Oversat til ikon)
            er_maal = str(row.get('SHOTISGOAL')).lower() == 'true'
            c[3].write("⚽ JA" if er_maal else "❌")
            
            # 5. SHOTXG
            c[4].write(str(row.get('SHOTXG', '0.00')))
            
            # 6. VENUE
            c[5].write(row.get('VENUE', 'N/A'))
            
            # 7. DATE
            c[6].write(str(row.get('DATE', 'N/A')))
