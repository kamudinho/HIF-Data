import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, spillere, hold_map):
    # --- DEBUG START (Fjern når vi har navnene) ---
    st.write("### Debug: Kolonner i Eventdata")
    st.write(list(df_events.columns))
    
    st.write("### Debug: Kolonner i Spillere-arket")
    st.write(list(spillere.columns))
    # --- DEBUG SLUT ---
    
    """
    df_events: 'ev' fra load_hif_data (har allerede PLAYER_NAME)
    spillere: 'sp' arket fra load_hif_data
    hold_map: Dictionary med team navne
    """
    HIF_ID = 38331
    HIF_RED = '#d31313'
    DARK_GREY = '#413B4D'

    # 1. FORBERED DATA (df_events har allerede PLAYER_NAME fra din loader)
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Filtrer til HIF afslutninger
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if 'TEAM_WYID' in df.columns:
        mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_s = df[mask].copy()
    
    # Konverter lokationer til tal
    df_s['LOCATIONX'] = pd.to_numeric(df_s['LOCATIONX'], errors='coerce')
    df_s['LOCATIONY'] = pd.to_numeric(df_s['LOCATIONY'], errors='coerce')
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_s.empty:
        st.info("Ingen afslutninger fundet for HIF.")
        return

    # Sorter kronologisk og generer det unikke nummer til prikkerne
    # Din loader sikrer PLAYER_NAME er med, så vi bruger den
    df_s = df_s.sort_values(by=['PERIOD', 'MINUTE', 'SECOND']).reset_index(drop=True)
    df_s['SHOT_NR'] = df_s.index + 1

    # 2. UI FILTRE
    # Vi bruger 'PLAYER_NAME', som du selv har oprettet i load_hif_data
    spiller_liste = sorted(df_s['PLAYER_NAME'].dropna().unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
    
    df_plot = df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['PLAYER_NAME'] == valgt_spiller]

    # 3. TEGN BANE (Matplotlib)
    # Wyscout koordinater kræver half=True for kun at se angrebssiden
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 6))
    ax.set_ylim(50, 102) 

    for _, row in df_plot.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        color = HIF_RED if is_goal else DARK_GREY
        
        # Prikken (Mål er større)
        ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                   s=600 if is_goal else 350, 
                   color=color, edgecolors='white', linewidth=1.5, alpha=0.9, zorder=3)
        
        # Løbenummeret (SHOT_NR) indeni cirklen
        ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NR'])), 
                color='white', ha='center', va='center', fontsize=9, fontweight='bold', zorder=4)

    # Layout centreret
    l, c, r = st.columns([0.1, 0.8, 0.1])
    with c:
        st.pyplot(fig)
        
        # 4. POPOVER INFORMATION
        with st.popover("🔎 Se detaljer om hver afslutning"):
            st.markdown(f"**Afslutninger: {valgt_spiller}**")
            
            # Formater tabel til popover
            tabel_df = df_plot.copy()
            tabel_df['MODSTANDER'] = tabel_df['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), "Ukendt"))
            tabel_df['RESULTAT'] = tabel_df['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            vis_tabel = tabel_df[['SHOT_NR', 'MINUTE', 'PLAYER_NAME', 'MODSTANDER', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Minut', 'Spiller', 'Modstander', 'Resultat']
            
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)
