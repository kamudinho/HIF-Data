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
    else:
        st.warning("Videofilen kunne ikke findes.")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Side (H/A):** {data.get('SIDE', 'N/A')}")
        # Kropsdel ligger i SHOTSBODYPART
        st.write(f"**Kropsdel:** {data.get('SHOTSBODYPART', 'N/A')}")
        
    with col2:
        # Mål-status ligger i SHOTISGOAL
        er_maal = str(data.get('SHOTISGOAL', 'false')).lower() == 'true'
        st.write(f"**Mål:** {'✅ JA' if er_maal else '❌ NEJ'}")
        
        # xG-tallet ligger i SHOTXG
        xg_val = data.get('SHOTXG', '0.00')
        st.metric("xG Værdi", f"{xg_val}")
        
        # Datoen ligger i DATE
        st.write(f"📅 **Dato:** {data.get('DATE', 'N/A')}")

    if st.button("Luk"):
        st.rerun()

# 2. Hovedfunktionen der viser siden
def vis_side(spillere):
    st.title("⚽ HIF Analyse-dashboard")
    
    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error(f"Kunne ikke finde filen: {csv_path}")
        return

    # Indlæs og rens CSV
    df = pd.read_csv(csv_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Rens ID'er
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x)))

    # Map videoer fra mappen
    video_map = {}
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        for f in video_filer:
            clean_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
            video_map[clean_id] = f

    # Filtrer så vi kun ser rækker med video
    video_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    if video_df.empty:
        st.info("Ingen matchende videoer fundet i mappen.")
        return

    st.subheader("Oversigt over afslutninger")
    
    # Overskrifter til tabellen
    t_cols = st.columns([1, 4, 2, 1, 1, 2])
    t_cols[0].write("**Video**")
    t_cols[1].write("**Kamp**")
    t_cols[2].write("**Kropsdel**")
    t_cols[3].write("**Mål**")
    t_cols[4].write("**xG**")
    t_cols[5].write("**ID**")
    st.divider()

    # DETTE LOOP ER NU INDRYKKET KORREKT INDE I FUNKTIONEN
    for idx, row in video_df.iterrows():
        c = st.columns([1, 4, 2, 1, 1, 2])
        
        # 1. Video knap
        if c[0].button("▶️", key=f"btn_{row['RENS_ID']}"):
            vis_video_popup(row, video_map.get(row['RENS_ID']), video_dir)
            
        # 2. Kamp (MATCHLABEL)
        c[1].write(row.get('MATCHLABEL', 'N/A'))
        
        # 3. Kropsdel (Nu fra SHOTSBODYPART jf. din struktur)
        c[2].write(row.get('SHOTSBODYPART', 'N/A'))
        
        # 4. Mål (Nu fra SHOTISGOAL jf. din struktur)
        er_maal = str(row.get('SHOTISGOAL')).lower() == 'true'
        c[3].write("⚽ JA" if er_maal else "❌")
        
        # 5. xG (Nu fra SHOTXG jf. din struktur)
        c[4].write(str(row.get('SHOTXG', '0.00')))
        
        # 6. ID
        c[5].write(f"`{row['RENS_ID']}`")
