import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- FARVER ---
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'

def vis_side(dp=None):
    st.markdown(f"""
        <div style="background-color:{HIF_RED}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">🎯 HVIDOVRE IF - OPTA SHOTMAP</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if not dp:
        st.error("Data pakke ikke fundet.")
        return

    # 1. HENT DATA
    df_shots = dp.get('playerstats', pd.DataFrame())
    df_matches = dp.get('opta_matches', pd.DataFrame())

    if df_shots.empty:
        st.info("Ingen Opta afslutninger fundet i systemet.")
        return

    # --- 2. DYNAMISK FIND KOLONNER (Løser 'DATE' fejlen) ---
    # Vi leder efter kolonnenavne der indeholder bestemte ord
    def find_col(df, keywords):
        for col in df.columns:
            if any(key in col for key in keywords):
                return col
        return None

    col_date = find_col(df_matches, ['DATE', 'TIMESTAMP'])
    col_home = find_col(df_matches, ['HOME', 'CONTESTANTHOME'])
    col_away = find_col(df_matches, ['AWAY', 'CONTESTANTAWAY'])
    col_match_id = find_col(df_matches, ['MATCH_OPTAUUID', 'MATCH_ID'])

    # --- 3. UI LAYOUT ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        # Kamp filter
        if not df_matches.empty and col_date and col_home:
            # Vi bygger beskrivelsen sikkert
            df_matches['DESC'] = (
                df_matches[col_date].astype(str).str[:10] + " - " + 
                df_matches[col_home].astype(str) + " v " + 
                df_matches[col_away].astype(str)
            )
            match_list = df_matches.sort_values(col_date, ascending=False)
            valgt_kamp = st.selectbox("Vælg Kamp", ["Alle Kampe"] + match_list['DESC'].tolist())
        else:
            valgt_kamp = "Alle Kampe"

        # Spiller filter
        spiller_col = find_col(df_shots, ['PLAYER_NAME', 'NAME'])
        spiller_liste = sorted(df_shots[spiller_col].dropna().unique().tolist()) if spiller_col else []
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle spillere"] + spiller_liste)
        
        vis_type = st.radio("Vis afslutninger:", ["Alle", "Kun mål"], horizontal=True)

    # --- 4. FILTRERING ---
    df_p = df_shots.copy()

    if valgt_kamp != "Alle Kampe" and col_match_id:
        m_id = df_matches[df_matches['DESC'] == valgt_kamp][col_match_id].iloc[0]
        # Find match_id kolonnen i shots (den hedder ofte MATCH_OPTAUUID)
        shot_match_col = find_col(df_shots, ['MATCH_OPTAUUID', 'MATCH_ID'])
        if shot_match_col:
            df_p = df_p[df_p[shot_match_col].astype(str) == str(m_id)]

    if valgt_spiller != "Alle spillere" and spiller_col:
        df_p = df_p[df_p[spiller_col] == valgt_spiller]

    outcome_col = find_col(df_shots, ['OUTCOME', 'IS_GOAL'])
    if vis_type == "Kun mål" and outcome_col:
        df_p = df_p[df_p[outcome_col].astype(str) == '1']

    # --- 5. STATS BOKS ---
    with col_stats:
        total_shots = len(df_p)
        total_goals = len(df_p[df_p[outcome_col].astype(str) == '1']) if outcome_col else 0
        xg_col = find_col(df_shots, ['XG', 'EXPECTED_GOALS'])
        total_xg = df_p[xg_col].sum() if xg_col else 0
        
        st.markdown(f"""
        <div style="border-left: 5px solid {HIF_RED}; padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
            <h4 style="margin:0;">{valgt_spiller if valgt_spiller != "Alle spillere" else "Hele holdet"}</h4>
            <hr>
            <h2 style="margin:0;">{total_shots} skud / {total_goals} mål</h2>
            <h2 style="margin:0;">{total_xg:.2f} total xG</h2>
        </div>
        """, unsafe_allow_html=True)

    # --- 6. TEGN KORTET ---
    with col_map:
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        # Golden Zone
        ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='gold', alpha=0.1, zorder=1))

        x_col = find_col(df_shots, ['EVENT_X', 'LOCATION_X', 'X'])
        y_col = find_col(df_shots, ['EVENT_Y', 'LOCATION_Y', 'Y'])

        if not df_p.empty and x_col and y_col:
            for i, row in df_p.reset_index().iterrows():
                is_goal = str(row[outcome_col]) == '1' if outcome_col else False
                color = HIF_RED if is_goal else HIF_BLUE
                sc_size = (row[xg_col] * 800) + 100 if xg_col else 200
                
                pitch.scatter(row[x_col], row[y_col], s=sc_size, c=color, 
                              edgecolors='white', ax=ax, zorder=3, alpha=0.8)
        
        st.pyplot(fig)
