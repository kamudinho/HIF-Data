import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, sp, hold_map):
    """
    df_events: Din eventdata.parquet
    sp: Dit Excel-ark 'Spillere' (læst som pd.read_excel)
    hold_map: Dictionary med team navne
    """
    HIF_ID = 38331
    HIF_RED = '#d31313'
    
    # --- 1. FORBERED SPILLER-MAPPING ---
    # Vi renser kolonnenavne i 'sp' arket for at undgå KeyErrors
    s_df = sp.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    # Vi tjekker om de nødvendige kolonner findes (efter rensning er de store)
    if 'PLAYER_WYID' in s_df.columns and 'NAVN' in s_df.columns:
        # Sikr at ID er en streng (f.eks. '12345') uden decimaler
        s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
        navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    else:
        st.error(f"Kunne ikke finde 'PLAYER_WYID' eller 'NAVN' i Spillere-arket. Fundne kolonner: {list(s_df.columns)}")
        return

    # --- 2. FORBERED EVENT-DATA ---
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Rens PLAYER_WYID i events så de kan matches med navne_dict
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    
    # Filtrer til HIF afslutninger (Wyscout primaryType indeholder 'shot')
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if 'TEAM_WYID' in df.columns:
        mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_skud = df[mask].copy()
    
    # Numeriske lokationer
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_skud.empty:
        st.info("Ingen afslutninger fundet for HIF.")
        return

    # Sorter kronologisk for at generere løbenummer (1, 2, 3...)
    # Vi tjekker hvilke tids-kolonner der er tilgængelige
    sort_cols = [c for c in ['PERIOD', 'MINUTE', 'SECOND'] if c in df_skud.columns]
    df_skud = df_skud.sort_values(by=sort_cols).reset_index(drop=True)
    
    # Her genereres det nummer, du skal bruge til at identificere prikken
    df_skud['SHOT_NUMBER'] = df_skud.index + 1
    
    # Tilføj spillernavnet fra 'sp' arket via vores dict
    df_skud['NAVN_OPLOOK'] = df_skud['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 3. BRUGERGRÆNSEFLADE (Filtre) ---
    spiller_options = sorted(df_skud['NAVN_OPLOOK'].unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_options)
    
    df_plot = df_skud if valgt_spiller == "Alle Spillere" else df_skud[df_skud['NAVN_OPLOOK'] == valgt_spiller]

    # --- 4. TEGN BANE (Matplotlib) ---
    # Vi bruger VerticalPitch til Wyscout-koordinater
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 6))
    ax.set_ylim(50, 102) # Zoomer ind på modstanderens halvdel

    for _, row in df_plot.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        color = HIF_RED if is_goal else '#413B4D'
        
        # Tegn prikken (større hvis det er mål)
        ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                   s=550 if is_goal else 350, 
                   color=color, edgecolors='white', linewidth=1.5, alpha=0.9, zorder=3)
        
        # Skriv SHOT_NUMBER indeni prikken
        ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NUMBER'])), 
                color='white', ha='center', va='center', fontsize=8, fontweight='bold', zorder=4)

    # Vis banen centreret i 70% bredde
    l, c, r = st.columns([0.15, 0.7, 0.15])
    with c:
        st.pyplot(fig)
        
        # --- 5. POPOVER (Information om afslutningerne) ---
        with st.popover("🔎 Se information om afslutninger"):
            st.markdown(f"**Detaljer for: {valgt_spiller}**")
            
            # Forbered tabel til visning
            vis_df = df_plot.copy()
            vis_df['MODSTANDER'] = vis_df['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {int(x)}") if pd.notna(x) else "Ukendt")
            vis_df['RESULTAT'] = vis_df['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            tabel_final = vis_df[['SHOT_NUMBER', 'MINUTE', 'NAVN_OPLOOK', 'MODSTANDER', 'RESULTAT']]
            tabel_final.columns = ['Nr.', 'Minut', 'Spiller', 'Modstander', 'Resultat']
            
            st.dataframe(tabel_final, hide_index=True, use_container_width=True)
