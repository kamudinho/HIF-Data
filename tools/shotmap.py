import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- KONFIGURATION (Fra dine værdier) ---
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#ffd700'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"
COMPETITION_ID = 328  # NordicBet Liga

def vis_side(dp, logo_map=None):
    # Hent playerstats fra datapakken
    # I din HIF-dash.py sender du dp["players"] eller hele dp. 
    # Vi sikrer os her, at vi får fat i dataframe-delen.
    if isinstance(dp, dict):
        df_raw = dp.get('playerstats', pd.DataFrame())
    else:
        df_raw = dp  # Hvis det allerede er en dataframe

    if df_raw.empty:
        st.warning("Ingen statistikker fundet i data.")
        return

    # --- 1. DATA RENS & FILTRERING ---
    # Filtrer på HIF og din specifikke liga (328)
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Konverter typer til strenge for sikkerhed
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip().str.upper()
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)

    # --- 2. DROPDOWN (ØVERST) ---
    spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste)

    # --- 3. TABS ---
    tab1, tab2 = st.tabs(["Skudkort", "Assists"])

    # --- TAB 1: SKUDKORT ---
    with tab1:
        # Skudtyper baseret på din liste (13-16, G, PG)
        skud_typer = ['13', '14', '15', '16', 'G', 'PG', '38']
        df_skud = df_hif[df_hif['TYPE_STR'].isin(skud_typer)].copy()
        
        if valgt_spiller != "Hele Holdet":
            df_skud = df_skud[df_skud['PLAYER_NAME'] == valgt_spiller]

        df_skud['ER_MAAL'] = df_skud['TYPE_STR'].isin(['16', 'G', 'PG'])

        col_map, col_stats = st.columns([2.5, 1])
        with col_map:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444')
            fig, ax = pitch.draw(figsize=(8, 10))
            
            for _, row in df_skud.iterrows():
                color = HIF_RED if row['ER_MAAL'] else HIF_BLUE
                size = (float(row.get('XG_VAL', 0.1)) * 1500) + 100
                # KUN CIRKLER - INGEN IKONER
                pitch.scatter(row['EVENT_X'], row['EVENT_Y'], s=size, c=color, 
                              marker='o', edgecolors='white', ax=ax, alpha=0.7, zorder=3)
            st.pyplot(fig)

        with col_stats:
            st.metric("Skud", len(df_skud))
            st.metric("Mål", int(df_skud['ER_MAAL'].sum()))
            st.metric("xG i alt", f"{df_skud['XG_VAL'].sum():.2f}")

    # --- TAB 2: ASSISTS ---
    with tab2:
        # Robust assist logik: Type 1 + Qualifier 210, eller Type AS
        # Vi bruger drop_duplicates for at sikre at tælleren er korrekt
        df_assists = df_hif[
            (df_hif['TYPE_STR'] == 'AS') | 
            (df_hif['QUAL_STR'].str.contains('210', na=False))
        ].copy()
        
        df_assists = df_assists.drop_duplicates(subset=['PLAYER_NAME', 'EVENT_X', 'EVENT_Y'])

        if valgt_spiller != "Hele Holdet":
            df_assists = df_assists[df_assists['PLAYER_NAME'] == valgt_spiller]

        col_map_a, col_stats_a = st.columns([2.5, 1])
        with col_map_a:
            # Half=True for at matche skudkortet
            pitch_a = VerticalPitch(half=True, pitch_type='opta', line_color='#444444')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
            
            if not df_assists.empty:
                for _, row in df_assists.iterrows():
                    ex = row.get('PASS_END_X', 98)
                    ey = row.get('PASS_END_Y', 50)
                    # Pile og cirkler i guld (HIF_GOLD)
                    pitch_a.arrows(row['EVENT_X'], row['EVENT_Y'], ex, ey, 
                                   color=HIF_GOLD, width=2, headwidth=4, ax=ax_a, zorder=2)
                    pitch_a.scatter(row['EVENT_X'], row['EVENT_Y'], color=HIF_GOLD, 
                                    marker='o', edgecolors='white', s=150, ax=ax_a, zorder=3)
            else:
                st.info("Ingen assists fundet.")
            st.pyplot(fig_a)

        with col_stats_a:
            st.metric("Assists", len(df_assists))
