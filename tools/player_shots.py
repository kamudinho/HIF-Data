import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    
    # --- 1. FORBERED NAVNE-MAPPING ---
    # Vi laver en kopi for ikke at ændre originalen
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    # Vi sikrer os, at ID'et er en streng uden decimaler (f.eks. '12345')
    if 'PLAYER_WYID' in s_df.columns and 'NAVN' in s_df.columns:
        s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
        navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    else:
        st.error("Kunne ikke finde 'PLAYER_WYID' eller 'NAVN' i df_spillere.")
        return

    # --- 2. FORBERED EVENT-DATA ---
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Rens PLAYER_WYID i events
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    
    # Filtrer til HIF afslutninger
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if 'TEAM_WYID' in df.columns:
        mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_skud = df[mask].copy()
    
    # Konverter koordinater (Wyscout format)
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_skud.empty:
        st.info("Ingen afslutninger fundet for HIF.")
        return

    # Sorter efter tid (Periode -> Minut -> Sekund) for korrekt rækkefølge
    sort_cols = [c for c in ['PERIOD', 'MINUTE', 'SECOND'] if c in df_skud.columns]
    df_skud = df_skud.sort_values(by=sort_cols).reset_index(drop=True)
    
    # GENERER LØBENUMMER (1, 2, 3...)
    df_skud['SHOT_NUMBER'] = df_skud.index + 1
    
    # Map NAVN på
    df_skud['VIS_NAVN'] = df_skud['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 3. UI FILTRE ---
    spiller_options = sorted(df_skud['VIS_NAVN'].unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_options)
    
    df_plot = df_skud if valgt_spiller == "Alle Spillere" else df_skud[df_skud['VIS_NAVN'] == valgt_spiller]

    # --- 4. MATPLOTLIB PLOT ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 6))
    ax.set_ylim(50, 102) # Zoom på modstanderens halvdel

    for _, row in df_plot.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        # Mål får HIF rød, almindelige skud får en mørkegrå
        prik_farve = HIF_RED if is_goal else '#413B4D'
        
        # Tegn prik
        ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                   s=550 if is_goal else 350, 
                   color=prik_farve, edgecolors='white', linewidth=1.5, alpha=0.9, zorder=3)
        
        # Indsæt løbenummeret i midten af prikken
        ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NUMBER'])), 
                color='white', ha='center', va='center', fontsize=8, fontweight='bold', zorder=4)

    # Layout optimering (70% bredde)
    l, c, r = st.columns([0.15, 0.7, 0.15])
    with c:
        st.pyplot(fig)
        
        # --- 5. POPOVER TABEL ---
        with st.popover("🔎 Se detaljer for afslutninger"):
            st.markdown(f"**Liste over afslutninger ({valgt_spiller})**")
            
            # Forbered tabelvisning
            tabel_df = df_plot.copy()
            tabel_df['MODSTANDER'] = tabel_df['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {int(x)}") if pd.notna(x) else "Ukendt")
            tabel_df['RESULTAT'] = tabel_df['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            vis_tabel = tabel_df[['SHOT_NUMBER', 'MINUTE', 'VIS_NAVN', 'MODSTANDER', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Minut', 'Spiller', 'Modstander', 'Resultat']
            
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)

    return df_skud # Returnerer data hvis du skal bruge det andre steder
