import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    
    # 1. RENS DATA
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Merge med spillere for at få rygnumre og navne
    s_df = df_spillere[['PLAYER_WYID', 'NAVN', 'NUMMER']].copy()
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    
    df = df.merge(s_df, on='PLAYER_WYID', how='left')

    # 2. FILTRERING (Skud for HIF)
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    mask &= (df['TEAM_WYID'].astype(int) == HIF_ID)
    
    df_skud = df[mask].copy()
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    # UI FILTRE
    spiller_liste = sorted(df_skud['NAVN'].dropna().unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle"] + spiller_liste)
    
    if valgt_spiller != "Alle":
        df_skud = df_skud[df_skud['NAVN'] == valgt_spiller]

    # --- 3. TEGN BANE ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444')
    fig, ax = pitch.draw(figsize=(10, 6))
    ax.set_ylim(50, 102) # Kompakt visning

    for i, row in df_skud.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        color = HIF_RED if is_goal else '#413B4D'
        size = 500 if is_goal else 300
        
        # Tegn prikken
        ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                   s=size, color=color, edgecolors='white', linewidth=1.5, alpha=0.9, zorder=3)
        
        # Indsæt rygnummer i prikken
        nummer = str(int(row['NUMMER'])) if pd.notna(row['NUMMER']) else "?"
        ax.text(row['LOCATIONY'], row['LOCATIONX'], nummer, 
                color='white', ha='center', va='center', fontsize=8, fontweight='bold', zorder=4)

    # Vis banen i 70% bredde
    col_l, col_c, col_r = st.columns([0.15, 0.7, 0.15])
    with col_c:
        st.pyplot(fig)

    # --- 4. POPOVER MED INFORMATION ---
    with col_c:
        with st.popover("🔎 Se skud-detaljer"):
            st.markdown(f"### Afslutninger for {valgt_spiller}")
            
            # Forbered tabel-data
            table_data = []
            for _, row in df_skud.iterrows():
                modstander = hold_map.get(int(row['OPPONENTTEAM_WYID']), "Ukendt")
                resultat = "⚽ MÅL" if 'goal' in str(row['PRIMARYTYPE']).lower() else "❌ Skud"
                table_data.append({
                    "Minut": f"{int(row['MINUTE'])}'",
                    "Spiller": row['NAVN'],
                    "Nr.": int(row['NUMMER']) if pd.notna(row['NUMMER']) else "-",
                    "Modstander": modstander,
                    "Resultat": resultat
                })
            
            if table_data:
                st.table(pd.DataFrame(table_data))
            else:
                st.write("Ingen data at vise.")
