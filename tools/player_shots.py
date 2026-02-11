import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    
    # 1. DATA RENS
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    # Find navne-kolonne
    col_navn = next((c for c in ['NAVN', 'PLAYER', 'PLAYER_NAME', 'SPILLER'] if c in s_df.columns), None)
    navne_dict = dict(zip(s_df['PLAYER_WYID'].astype(str).str.split('.').str[0], s_df[col_navn]))

    # 2. FILTRERING (HIF Skud)
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_skud = df[mask].copy()
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_skud.empty:
        st.info("Ingen skud fundet for HIF.")
        return

    # Sorter efter minut for at få en logisk rækkefølge (1, 2, 3...)
    df_skud = df_skud.sort_values(by='MINUTE').reset_index(drop=True)
    # GENERER LØBENUMMER (starter fra 1)
    df_skud['SHOT_ID'] = df_skud.index + 1

    # UI FILTRE
    spiller_navne = sorted([navne_dict.get(str(pid).split('.')[0], "Ukendt") for pid in df_skud['PLAYER_WYID'].unique()])
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_navne)
    
    # Filtrer plot-data (vi beholder SHOT_ID fra den samlede liste)
    if valgt_spiller == "Alle Spillere":
        df_plot = df_skud
    else:
        df_plot = df_skud[df_skud['PLAYER_WYID'].astype(str).str.split('.').str[0].map(navne_dict) == valgt_spiller]

    # --- 3. TEGN BANE ---
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
        
        # --- 4. POPOVER MED IDENTIFIKATION ---
        with st.popover("🔎 Identificér afslutninger"):
            st.write("Numrene på banen svarer til listen herunder:")
            
            # Byg overskuelig tabel
            info_rows = []
            for _, row in df_plot.iterrows():
                p_id = str(row['PLAYER_WYID']).split('.')[0]
                info_rows.append({
                    "ID": int(row['SHOT_ID']),
                    "Minut": f"{int(row['MINUTE'])}'",
                    "Spiller": navne_dict.get(p_id, "Ukendt"),
                    "Modstander": hold_map.get(int(row['OPPONENTTEAM_WYID']), "Ukendt"),
                    "Type": "⚽ MÅL" if 'goal' in str(row['PRIMARYTYPE']).lower() else "❌ Skud"
                })
            
            st.dataframe(pd.DataFrame(info_rows), hide_index=True, use_container_width=True)
