import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    
    # --- 1. FORBERED SPILLER-ARKET ---
    s_df = df_spillere.copy()
    # Rens kolonnenavne i spiller-arket
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    # Tjek om vi har de rigtige kolonner i spiller-arket
    if 'PLAYER_WYID' not in s_df.columns or 'NAVN' not in s_df.columns:
        st.error(f"Fejl: Spiller-arket mangler 'PLAYER_WYID' eller 'NAVN'. Fundne kolonner: {list(s_df.columns)}")
        return

    # Lav en dictionary til hurtig opslag af navne {ID: NAVN}
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))

    # --- 2. FORBERED EVENT-DATA ---
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Rens PLAYER_WYID i event-data så de kan matches
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    
    # Filtrer til kun HIF afslutninger
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_skud = df[mask].copy()
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_skud.empty:
        st.info("Ingen afslutninger fundet for HIF.")
        return

    # Sorter efter tid og generer løbenummer (1, 2, 3...)
    df_skud = df_skud.sort_values(by=['PERIOD', 'MINUTE', 'SECOND']).reset_index(drop=True)
    df_skud['SHOT_ID'] = df_skud.index + 1

    # Tilføj spillernavne fra spiller-arket
    df_skud['NAVN_FRA_ARK'] = df_skud['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 3. UI FILTRE ---
    spiller_liste = sorted(df_skud['NAVN_FRA_ARK'].unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
    
    df_plot = df_skud if valgt_spiller == "Alle Spillere" else df_skud[df_skud['NAVN_FRA_ARK'] == valgt_spiller]

    # --- 4. TEGN BANE (Matplotlib) ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 5))
    ax.set_ylim(50, 102)

    for _, row in df_plot.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        color = HIF_RED if is_goal else '#413B4D'
        
        # Tegn cirklen
        ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                   s=450 if is_goal else 250, 
                   color=color, edgecolors='white', linewidth=1.2, alpha=0.9, zorder=3)
        
        # Skriv løbenummeret indeni cirklen
        ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_ID'])), 
                color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)

    # Centrer banen
    l, c, r = st.columns([0.15, 0.7, 0.15])
    with c:
        st.pyplot(fig)
        
        # --- 5. POPOVER MED INFORMATION ---
        with st.popover("🔎 Se detaljer for afslutninger"):
            st.markdown(f"**Viser data for: {valgt_spiller}**")
            
            # Forbered data til tabellen
            tabel_data = df_plot.copy()
            tabel_data['MODSTANDER'] = tabel_data['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {int(x)}") if pd.notna(x) else "Ukendt")
            tabel_data['RESULTAT'] = tabel_data['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            vis_df = tabel_data[['SHOT_ID', 'MINUTE', 'NAVN_FRA_ARK', 'MODSTANDER', 'RESULTAT']]
            vis_df.columns = ['Nr.', 'Minut', 'Spiller', 'Modstander', 'Resultat']
            
            st.dataframe(vis_df, hide_index=True, use_container_width=True)
