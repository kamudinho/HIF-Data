import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- KONFIGURATION & BRANDING ---
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'

def vis_side(dp=None):
    st.markdown(f"""
        <div style="background-color:{HIF_RED}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">🎯 HVIDOVRE IF - OPTA SHOTMAP</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Hent data fra din pakke (playerstats er din nye opta_shotevents query)
    df_shots = dp.get('playerstats', pd.DataFrame())
    df_matches = dp.get('opta_matches', pd.DataFrame())

    if df_shots.empty:
        st.info("Ingen Opta afslutninger fundet i systemet for den valgte periode.")
        return

    # --- 1. UI LAYOUT & VALG ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        # Kamp filter
        if not df_matches.empty:
            df_matches['DESC'] = (df_matches['DATE'].astype(str) + " - " + 
                                 df_matches['HOMECONTESTANT_NAME'] + " v " + 
                                 df_matches['AWAYCONTESTANT_NAME'])
            match_list = df_matches.sort_values('DATE', ascending=False)
            valgt_kamp = st.selectbox("Vælg Kamp", ["Alle Kampe"] + match_list['DESC'].tolist())
        else:
            valgt_kamp = "Alle Kampe"

        # Spiller filter
        spiller_liste = sorted(df_shots['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle spillere"] + spiller_liste)
        
        vis_type = st.radio("Vis afslutninger:", ["Alle", "Kun mål"], horizontal=True)

    # --- 2. FILTRERING AF DATA ---
    df_p = df_shots.copy()

    # Filtrér på kamp
    if valgt_kamp != "Alle Kampe":
        m_id = df_matches[df_matches['DESC'] == valgt_kamp]['MATCH_OPTAUUID'].iloc[0]
        df_p = df_p[df_p['MATCH_OPTAUUID'] == m_id]

    # Filtrér på spiller
    if valgt_spiller != "Alle spillere":
        df_p = df_p[df_p['PLAYER_NAME'] == valgt_spiller]

    # Filtrér på mål
    if vis_type == "Kun mål":
        df_p = df_p[df_p['EVENT_OUTCOME'].astype(str) == '1']

    # --- 3. STATISTIK BOKS ---
    with col_stats:
        total_shots = len(df_p)
        total_goals = len(df_p[df_p['EVENT_OUTCOME'].astype(str) == '1'])
        total_xg = df_p['XG_VAL'].sum()
        conv_rate = (total_goals / total_shots * 100) if total_shots > 0 else 0

        st.markdown(f"""
        <div style="border-left: 5px solid {HIF_RED}; padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
            <h4 style="margin:0;">{valgt_spiller if valgt_spiller != "Alle spillere" else "Hele holdet"}</h4>
            <hr>
            <small>SKUD / MÅL</small>
            <h2 style="margin:0;">{total_shots} / {total_goals}</h2>
            <br>
            <small>KONVERTERINGSRATE</small>
            <h2 style="margin:0;">{conv_rate:.1f}%</h2>
            <br>
            <small>TOTAL xG</small>
            <h2 style="margin:0;">{total_xg:.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    # --- 4. TEGN KORTET ---
    with col_map:
        # Vigtigt: pitch_type='opta' da Opta koordinater er 0-100
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        # Golden Zone
        ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='gold', alpha=0.1, zorder=1))

        if not df_p.empty:
            for i, row in df_p.reset_index().iterrows():
                color = HIF_RED if str(row['EVENT_OUTCOME']) == '1' else HIF_BLUE
                # Størrelse baseret på xG
                sc_size = (row['XG_VAL'] * 800) + 100
                # Marker: Trekant for hovedstød (Qualifier 15)
                marker = '^' if '15' in str(row.get('QUALIFIERS', '')) else 'o'
                
                pitch.scatter(row['EVENT_X'], row['EVENT_Y'], 
                              s=sc_size, c=color, marker=marker,
                              edgecolors='white', ax=ax, zorder=3, alpha=0.8)
                
                # Nummerering (valgfrit)
                ax.text(row['EVENT_Y'], row['EVENT_X'], str(i+1), 
                        color='white', ha='center', va='center', fontsize=7, zorder=4)
        
        st.pyplot(fig)
        st.caption("Cirkel = Fod | Trekant = Hovedstød | Størrelse = xG")
