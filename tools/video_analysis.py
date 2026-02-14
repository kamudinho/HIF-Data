import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere):
    st.title("⚽ Analyse-dashboard")
    st.write("Klik på ▶️ for at se videoen og detaljer for den enkelte afslutning.")

    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    if not os.path.exists(csv_path):
        st.error("Kunne ikke finde matches.csv")
        return

    # 1. Indlæs og rens data
    df = pd.read_csv(csv_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [re.sub(r'\W+', '', c).upper() for c in df.columns]
    
    # Lav rensede ID'er til match mod videofiler
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x)))

    # 2. Find alle tilgængelige videoer i mappen
    video_map = {}
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        for f in video_filer:
            # Fjern .mp4 før rensning for at undgå det ekstra 4-tal
            clean_id = "".join(re.findall(r'\d+', os.path.splitext(f)[0]))
            video_map[clean_id] = f

    # 3. Forbered data til tabellen
    # Vi markerer rækker, hvor vi faktisk har en video
    df['VIDEO_STATUS'] = df['RENS_ID'].apply(lambda x: "▶️ Se video" if x in video_map else "Mangler ❌")

    # 4. Vis tabellen (Vi viser kun de vigtigste kolonner for overblik)
    # Vi bruger st.dataframe eller st.data_editor, men for knapper bruger vi kolonner
    st.subheader("Alle afslutninger")
    
    # Overskrifter
    cols = st.columns([1, 4, 2, 1, 1, 2])
    cols[0].write("**Video**")
    cols[1].write("**Kamp**")
    cols[2].write("**Kropsdel**")
    cols[3].write("**Mål**")
    cols[4].write("**xG**")
    cols[5].write("**ID**")
    st.divider()

    # Loop gennem de første X rækker (eller filtrer efter behov)
    # For performance viser vi her de 50 første rækker, eller dem med video
    display_df = df[df['VIDEO_STATUS'] == "▶️ Se video"].head(50)

    for idx, row in display_df.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1, 4, 2, 1, 1, 2])
        
        if c1.button("▶️", key=f"btn_{row['RENS_ID']}"):
            vis_video_popup(row, video_map.get(row['RENS_ID']), video_dir)
            
        c2.write(row.get('MATCHLABEL', 'N/A'))
        c3.write(row.get('SHOTBODYPART', 'N/A'))
        
        maal = "⚽ JA" if str(row.get('SHOTISGOAL')).lower() == 'true' else "❌"
        c4.write(maal)
        
        # SIKKER KONVERTERING AF xG
        try:
            # Vi fjerner eventuelle kommaer og erstatter med punktum, før vi konverterer
            xg_raw = str(row.get('SHOTXG', '0')).replace(',', '.')
            xg_val = float(xg_raw)
            c5.write(f"{xg_val:.2f}")
        except (ValueError, TypeError):
            # Hvis dataen er ødelagt eller tom, skriver vi 0.00
            c5.write("0.00")
            
        c6.write(f"`{row['RENS_ID']}`")

# 5. Funktionen der laver din Pop-up (Modal)
@st.dialog("Videoanalyse")
def vis_video_popup(data, filnavn, video_dir):
    st.subheader(f"{data['MATCHLABEL']}")
    
    if filnavn:
        video_sti = os.path.join(video_dir, filnavn)
        st.video(video_sti)
    else:
        st.warning("Videofilen blev ikke fundet i mappen.")

    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Resultat:** {data.get('RESULT', 'N/A')}")
        st.write(f"**Side:** {data.get('SIDE', 'N/A')}")
    with col2:
        st.write(f"**xG Værdi:** {data.get('SHOTXG', '0.00')}")
        st.write(f"**Kropsdel:** {data.get('SHOTBODYPART', 'N/A')}")
    
    if st.button("Luk"):
        st.rerun()
