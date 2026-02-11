import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    """
    Viser en kompakt skudoversigt med løbenumre.
    """
    HIF_ID = 38331
    HIF_RED = '#d31313'
    DARK_GREY = '#413B4D'

    # --- 1. KLARGØR SPILLER-DATA ---
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    # Mapping logik for navne
    s_df['FULL_NAME'] = s_df.apply(
        lambda x: f"{x.get('FIRSTNAME', '')} {x.get('LASTNAME', '')}".strip() if pd.notna(x.get('FIRSTNAME')) or pd.notna(x.get('LASTNAME')) else x.get('NAVN', "-"),
        axis=1
    )
    
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['FULL_NAME']))

    # --- 2. KLARGØR EVENTDATA ---
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    # Filtrer til HIF skud
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if 'TEAM_WYID' in df.columns:
        mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_s = df[mask].copy()
    
    # Lokationer og rensning
    df_s['LOCATIONX'] = pd.to_numeric(df_s['LOCATIONX'], errors='coerce')
    df_s['LOCATIONY'] = pd.to_numeric(df_s['LOCATIONY'], errors='coerce')
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_s.empty:
        st.info("Ingen afslutninger fundet for HIF.")
        return

    # Sorter kronologisk og generer løbenummer
    df_s = df_s.sort_values(by='MINUTE').reset_index(drop=True)
    df_s['SHOT_NR'] = df_s.index + 1
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 3. UI FILTRE ---
    spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
    
    df_plot = df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller]

    # --- 4. TEGN KOMPAKT BANE ---
    # pad_bottom fjerner tom plads mod midterlinjen
    pitch = VerticalPitch(
        half=True, 
        pitch_type='wyscout', 
        line_color='#444444', 
        line_zorder=2,
        pad_bottom=-15 
    )
    
    # Mindre figsize for at matche zone-visningen
    fig, ax = pitch.draw(figsize=(7, 4.5))
    
    # Zoom ind på den relevante del (fra 65 til 102 i Wyscout-koordinater)
    ax.set_ylim(65, 102) 

    for _, row in df_plot.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        color = HIF_RED if is_goal else DARK_GREY
        
        # Prikken
        ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                   s=350 if is_goal else 180, 
                   color=color, edgecolors='white', linewidth=1.0, alpha=0.9, zorder=3)
        
        # Løbenummer med skriftstørrelse 6
        ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NR'])), 
                color='white', ha='center', va='center', fontsize=6, fontweight='bold', zorder=4)

    # --- 5. VISNING I STREAMLIT ---
    # Vi bruger smalle side-kolonner for at tvinge banen til at være mindre og centreret
    l, c, r = st.columns([0.25, 0.5, 0.25])
    with c:
        st.pyplot(fig)
        
        # Popover placeret direkte under den kompakte bane
        with st.popover(f"🔎 Detaljer for {valgt_spiller}"):
            tabel_df = df_plot.copy()
            tabel_df['MODSTANDER'] = tabel_df['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {x}"))
            tabel_df['RESULTAT'] = tabel_df['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            vis_tabel = tabel_df[['SHOT_NR', 'MINUTE', 'SPILLER_NAVN', 'MODSTANDER', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Minut', 'Spiller', 'Modstander', 'Resultat']
            
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)
