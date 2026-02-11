import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    """
    df_events: Din eventdata.parquet
    df_spillere: Dit 'sp' ark (det du lige sendte koden til)
    hold_map: Dictionary med team navne
    """
    HIF_ID = 38331
    HIF_RED = '#d31313'
    DARK_GREY = '#413B4D'

    # --- 1. SKAB NAVNE-MAPPING FRA DIN SPILLER-LOGIK ---
    s_df = df_spillere.copy()
    
    # Vi genskaber 'FULL_NAME' logikken fra din hovedfil for konsistens
    s_df['FULL_NAME'] = s_df.apply(
        lambda x: f"{x['FIRSTNAME']} {x['LASTNAME']}".strip() if pd.notna(x.get('FIRSTNAME')) or pd.notna(x.get('LASTNAME')) else x.get('NAVN', "-"),
        axis=1
    )
    
    # Lav ordbog: {PLAYER_WYID: FULL_NAME}
    # Vi sikrer os at PLAYER_WYID er strenge uden .0 til sidst
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['FULL_NAME']))

    # --- 2. FORBERED EVENTDATA ---
    df = df_events.copy()
    
    # Rens PLAYER_WYID i eventdata så de kan matches
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    # Filtrer til HIF afslutninger (shot / goal)
    # Vi bruger PRIMARYTYPE og TEAM_WYID fra din debug
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

    # Sorter kronologisk efter minut og sekund hvis de findes
    sort_cols = [c for c in ['MINUTE', 'SECOND'] if c in df_s.columns]
    df_s = df_s.sort_values(by=sort_cols).reset_index(drop=True)
    
    # Løbenummer til identifikation på banen
    df_s['SHOT_NR'] = df_s.index + 1
    
    # Map det pæne navn på fra spillere-arket
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 3. UI FILTRE ---
    spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
    
    df_plot = df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller]

    # --- 4. TEGN BANE (Wyscout format) ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 6))
    ax.set_ylim(50, 102) 

    for _, row in df_plot.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        color = HIF_RED if is_goal else DARK_GREY
        
        # Prikken
        ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                   s=600 if is_goal else 350, 
                   color=color, edgecolors='white', linewidth=1.5, alpha=0.9, zorder=3)
        
        # Nummeret indeni prikken (matcher SHOT_NR)
        ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NR'])), 
                color='white', ha='center', va='center', fontsize=9, fontweight='bold', zorder=4)

    # Visning i appen
    l, c, r = st.columns([0.05, 0.9, 0.05])
    with c:
        st.pyplot(fig)
        
        # --- 5. POPOVER MED DETALJER ---
        with st.popover(f"🔎 Se detaljer: {valgt_spiller}"):
            tabel_df = df_plot.copy()
            tabel_df['MODSTANDER'] = tabel_df['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {x}"))
            tabel_df['RESULTAT'] = tabel_df['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            # Vis tabellen
            vis_tabel = tabel_df[['SHOT_NR', 'MINUTE', 'SPILLER_NAVN', 'MODSTANDER', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Minut', 'Spiller', 'Modstander', 'Resultat']
            
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)
