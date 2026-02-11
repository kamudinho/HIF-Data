import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    
    # --- 1. ROBUST KOLONNE-IDENTIFIKATION ---
    # Vi tvinger alle kolonnenavne til UPPERCASE og fjerner mellemrum
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]

    # Find ID-kolonnen i spiller-filen (kan hedde PLAYER_WYID, WYID, ID, etc.)
    col_spiller_id = next((c for c in ['PLAYER_WYID', 'WYID', 'ID', 'PLAYERID'] if c in s_df.columns), None)
    # Find Navne-kolonnen
    col_navn = next((c for c in ['NAVN', 'PLAYER', 'PLAYER_NAME', 'SPILLER'] if c in s_df.columns), None)

    if not col_spiller_id or not col_navn:
        st.error(f"Kunne ikke finde ID eller Navn i spiller-filen. Kolonner fundet: {list(s_df.columns)}")
        return

    # Lav en ordbog: {ID: Navn}
    s_df[col_spiller_id] = s_df[col_spiller_id].astype(str).str.split('.').str[0]
    navne_dict = dict(zip(s_df[col_spiller_id], s_df[col_navn]))

    # --- 2. FILTRERING (HIF Skud) ---
    # Find ID-kolonnen i events (typisk PLAYER_WYID)
    col_event_player = next((c for c in ['PLAYER_WYID', 'PLAYERID'] if c in df.columns), 'PLAYER_WYID')
    
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    # Sikr os at TEAM_WYID tjekkes korrekt
    if 'TEAM_WYID' in df.columns:
        mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_skud = df[mask].copy()
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_skud.empty:
        st.info("Ingen skud fundet for HIF.")
        return

    # Sorter efter minut og generer løbenummer
    df_skud = df_skud.sort_values(by='MINUTE').reset_index(drop=True)
    df_skud['SHOT_ID'] = df_skud.index + 1

    # --- 3. UI FILTRE ---
    # Map navne til de spillere der rent faktisk har skudt
    df_skud['SPILLER_NAVN'] = df_skud[col_event_player].astype(str).str.split('.').str[0].map(navne_dict).fillna("Ukendt Spiller")
    
    spiller_liste = sorted(df_skud['SPILLER_NAVN'].unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
    
    df_plot = df_skud if valgt_spiller == "Alle Spillere" else df_skud[df_skud['SPILLER_NAVN'] == valgt_spiller]

    # --- 4. TEGN BANE ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 5))
    ax.set_ylim(50, 102)

    for _, row in df_plot.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        color = HIF_RED if is_goal else '#413B4D'
        
        # Prikken
        ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                   s=450 if is_goal else 250, 
                   color=color, edgecolors='white', linewidth=1.2, alpha=0.9, zorder=3)
        
        # LØBENUMMER i prikken
        ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_ID'])), 
                color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)

    # Visning i 70% bredde
    l, c, r = st.columns([0.15, 0.7, 0.15])
    with c:
        st.pyplot(fig)
        
        # --- 5. POPOVER MED TABEL ---
        with st.popover("🔎 Se detaljer for afslutninger"):
            st.write(f"Viser detaljer for: **{valgt_spiller}**")
            
            info_df = df_plot[['SHOT_ID', 'MINUTE', 'SPILLER_NAVN', 'OPPONENTTEAM_WYID', 'PRIMARYTYPE']].copy()
            info_df['MODSTANDER'] = info_df['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {int(x)}") if pd.notna(x) else "Ukendt")
            info_df['RESULTAT'] = info_df['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            # Formater til visning
            vis_tabel = info_df[['SHOT_ID', 'MINUTE', 'SPILLER_NAVN', 'MODSTANDER', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Minut', 'Spiller', 'Modstander', 'Resultat']
            
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)
