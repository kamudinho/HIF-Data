import streamlit as st
import pandas as pd
import os
import re
from mplsoccer import VerticalPitch

def vis_side(dummy_input):
    st.title("HIF Mål-oversigt")
    
    # 1. Stier
    match_path = 'data/matches.csv'
    player_path = 'data/players.csv'
    video_dir = 'videos'

    if not os.path.exists(match_path):
        st.error(f"Mangler {match_path}")
        return

    # 2. Indlæs og map navne
    df = pd.read_csv(match_path, encoding='utf-8-sig', sep=None, engine='python')
    df.columns = [c.strip().upper() for c in df.columns]

    if os.path.exists(player_path):
        p_df = pd.read_csv(player_path, encoding='utf-8-sig', sep=None, engine='python')
        p_df.columns = [c.strip().upper() for c in p_df.columns]
        # Mapper PLAYER_WYID (som tekst) til NAVN
        navne_map = dict(zip(p_df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False), p_df['NAVN']))
    else:
        navne_map = {}

    # Indsæt spillernavne i match-data
    df['SPILLER'] = df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False).map(navne_map).fillna(df['PLAYER_WYID'])

    # 3. Find videoer (uden at stjæle 4-tallet fra .mp4)
    video_map = {}
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.lower().endswith('.mp4'):
                # Fjerner .mp4 FØR rensning for tal
                rent_navn = os.path.splitext(f)[0]
                clean_id = "".join(re.findall(r'\d+', rent_navn))
                video_map[clean_id] = f

    # 4. Rens CSV ID'er og filtrer til dem med video
    df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x.split('.')[0])))
    tabel_df = df[df['RENS_ID'].isin(video_map.keys())].copy()

    # 5. Visning - Vi starter med alle mål på banen
    st.subheader("Sæsonens mål")
    
    # Filtrer så vi kun viser mål i tabellen og på banen
    maal_df = tabel_df[tabel_df['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', 't'])].copy()
    maal_df['NR'] = range(1, len(maal_df) + 1)

    col1, col2 = st.columns([2, 1])

    with col2:
        # Liste over mål
        with st.popover("Se målliste", use_container_width=True):
            for idx, row in maal_df.iterrows():
                c_id, c_navn, c_btn = st.columns([1, 3, 2])
                c_id.write(f"#{row['NR']}")
                c_navn.write(f"**{row['SPILLER']}**\n{row['MATCHLABEL']}")
                
                # Video knap
                if c_btn.button("Se", key=f"btn_{row['RENS_ID']}"):
                    st.session_state['active_video'] = os.path.join(video_dir, video_map[row['RENS_ID']])

        if 'active_video' in st.session_state:
            st.video(st.session_state['active_video'])

    with col1:
        # Bane med alle mål
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444')
        fig, ax = pitch.draw()
        
        for _, row in maal_df.iterrows():
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], s=150, color='gold', edgecolors='white', zorder=3)
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(row['NR']), 
                    color='black', ha='center', va='center', fontsize=6, fontweight='bold')
        
        st.pyplot(fig)
