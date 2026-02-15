import streamlit as st
import pandas as pd
import os
import re

# 1. Funktionen til din Pop-up (Modal)
@st.dialog("Videoanalyse")
def vis_video_popup(data, filnavn, video_dir):
    st.subheader(f"{data.get('MATCHLABEL', 'Kamp-data')}")
    
    if filnavn:
        st.video(os.path.join(video_dir, filnavn))
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        # Nu hvor RESULT er væk, rykker data én plads til venstre:
        # SIDE indeholder nu RESULT/Score-info (home/away)
        st.write(f"**Side (H/A):** {data.get('RESULT', 'N/A')}") 
        # SHOTSBODYPART indeholder nu kropsdel (f.eks. left_foot)
        st.write(f"**Kropsdel:** {data.get('SIDE', 'N/A')}")
        
    with col2:
        # SHOTISGOAL indeholder nu True/False for mål
        er_maal = str(data.get('SHOTSBODYPART', 'false')).lower() == 'true'
        st.write(f"**Mål:** {'✅ JA' if er_maal else '❌ NEJ'}")
        
        # SHOTXG indeholder nu selve xG-værdien
        st.metric("xG Værdi", f"{data.get('SHOTISGOAL', '0.00')}")
        
        # DATE indeholder nu datoen
        st.write(f"📅 **Dato:** {data.get('SHOTXG', 'N/A')}")

# 2. Hovedfunktionen
def vis_side(spillere):
    st.title("⚽ HIF Analyse-dashboard")
    
    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error("Kunne ikke finde matches.csv")
        return

    df = pd.read_csv(csv_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x)))

    video_map = {}
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        for f in video_filer:
            clean_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
            video_map[clean_id] = f

    video_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    if video_df.empty:
        st.info("Ingen matchende videoer fundet.")
        return

    # TABEL-VISNING
    t_cols = st.columns([1, 4, 2, 1, 1, 2])
    t_cols[0].write("**Video**")
    t_cols[1].write("**Kamp**")
    t_cols[2].write("**Kropsdel**")
    t_cols[3].write("**Mål**")
    t_cols[4].write("**xG**")
    t_cols[5].write("**ID**")
    st.divider()

    for idx, row in video_df.iterrows():
        c = st.columns([1, 4, 2, 1, 1, 2])
        
        if c[0].button("▶️", key=f"btn_{row['RENS_ID']}"):
            vis_video_popup(row, video_map.get(row['RENS_ID']), video_dir)
            
        c[1].write(row.get('MATCHLABEL', 'N/A'))
        
        # NY MAPPING EFTER FJERNELSE AF RESULT:
        # Kropsdel ligger nu i 'SIDE'
        c[2].write(row.get('SIDE', 'N/A'))
        
        # Mål (True/False) ligger nu i 'SHOTSBODYPART'
        er_maal = str(row.get('SHOTSBODYPART')).lower() == 'true'
        c[3].write("⚽ JA" if er_maal else "❌")
        
        # xG-værdi ligger nu i 'SHOTISGOAL'
        xg_val = row.get('SHOTISGOAL', '0.00')
        c[4].write(f"{xg_val}")
        
        c[5].write(f"`{row['RENS_ID']}`")
