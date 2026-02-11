import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, sp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    DARK_GREY = '#413B4D'

    # 1. FORBERED NAVNE-MAPPING FRA SPILLERE-ARKET
    s_df = sp.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    # Lav ordbog: {PLAYER_WYID: NAVN}
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))

    # 2. FORBERED EVENTDATA
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Rens PLAYER_WYID i eventdata
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]

    # Filtrer til HIF afslutninger
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_s = df[mask].copy()
    
    # Lokationer
    df_s['LOCATIONX'] = pd.to_numeric(df_s['LOCATIONX'], errors='coerce')
    df_s['LOCATIONY'] = pd.to_numeric(df_s['LOCATIONY'], errors='coerce')
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_s.empty:
        st.info("Ingen afslutninger fundet for HIF.")
        return

    # Sorter og generer løbenummer
    df_s = df_s.sort_values(by='MINUTE').reset_index(drop=True)
    df_s['SHOT_NR'] = df_s.index + 1
    
    # Hent det rigtige NAVN baseret på PLAYER_WYID
    df_s['VIS_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # 3. UI FILTRE
    spiller_liste = sorted(df_s['VIS_NAVN'].unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
    
    df_plot = df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['VIS_NAVN'] == valgt_spiller]

    # --- 4. TEGN BANE ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 6))
    ax.set_ylim(50, 102) 

    for _, row in df_plot.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        color = HIF_RED if is_goal else DARK_GREY
        
        ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                   s=600 if is_goal else 350, 
                   color=color, edgecolors='white', linewidth=1.5, alpha=0.9, zorder=3)
        
        # Nummeret refererer til SHOT_NR (løbenummeret)
        ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NR'])), 
                color='white', ha='center', va='center', fontsize=9, fontweight='bold', zorder=4)

    # Visning
    l, c, r = st.columns([0.1, 0.8, 0.1])
    with c:
        st.pyplot(fig)
        
        # 5. POPOVER
        with st.popover(f"🔎 Detaljer: {valgt_spiller}"):
            tabel_df = df_plot.copy()
            tabel_df['MODSTANDER'] = tabel_df['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {x}"))
            tabel_df['RESULTAT'] = tabel_df['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            vis_tabel = tabel_df[['SHOT_NR', 'MINUTE', 'VIS_NAVN', 'MODSTANDER', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Minut', 'Spiller', 'Modstander', 'Resultat']
            
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)
