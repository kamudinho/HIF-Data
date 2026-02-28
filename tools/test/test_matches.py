import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(df):
    # --- 1. BRANDING ---
    hif_rod = "#df003b"
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">TURNERING: KAMPOVERSIGT (OPTA)</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.info("Ingen data fundet.")
        return

    # --- 2. RENS NAVNE (Standardiserer til store bogstaver internt) ---
    # 1. Standardiser kolonner (VIGTIGT: Snowflake returnerer altid UPPERCASE)
    df.columns = [c.upper() for c in df.columns]
    
    # 2. MATCHLABEL FIX
    # Opta-data har ofte ikke 'MATCHLABEL'. Vi bygger den selv hvis den mangler.
    if 'MATCHLABEL' not in df.columns:
        # Tjek om vi har de specifikke Opta navne fra din SQL
        home = df.get('CONTESTANTHOME_NAME', df.get('HOME_TEAM_NAME', 'Hjemme'))
        away = df.get('CONTESTANTAWAY_NAME', df.get('AWAY_TEAM_NAME', 'Ude'))
        df['KAMP_RENSET'] = home + " - " + away
    else:
        df['KAMP_RENSET'] = df['MATCHLABEL'].str.split(',').str[0]

    # 3. DATO FIX (Opta bruger MATCH_DATE_FULL)
    # Vi prøver alle muligheder for dato-kolonnen
    dato_col = next((c for c in ['DATE', 'MATCH_DATE_FULL', 'DATE_DT'] if c in df.columns), None)
    if dato_col:
        df['DATE_DT'] = pd.to_datetime(df[dato_col])
    else:
        df['DATE_DT'] = pd.Timestamp.now()
    
    df = df.sort_values('DATE_DT', ascending=False)
    df['VISNINGSDATO'] = df['DATE_DT'].dt.strftime('%d-%m-%Y')

    # 4. MÅL FIX (Håndterer Opta's TOTAL_HOME_SCORE)
    def get_score(row):
        h = row.get('TOTAL_HOME_SCORE', row.get('HOME_GOALS', 0))
        a = row.get('TOTAL_AWAY_SCORE', row.get('AWAY_GOALS', 0))
        # Hvis kampen er spillet (Played) eller har score
        if pd.notna(h) and pd.notna(a):
            return f"{int(float(h))} - {int(float(a))}"
        return "-"

    df['MÅL'] = df.apply(get_score, axis=1)

    # 5. KLARGØR TIL TABEL
    # Vi sikrer os at Rd. (WEEK) findes
    df['RD_VIS'] = df.get('WEEK', df.get('GAMEWEEK', 0))
    
    # Vælg de endelige kolonner (brug de navne vi lige har lavet i UPPERCASE)
    final_cols = ['VISNINGSDATO', 'RD_VIS', 'KAMP_RENSET', 'MÅL', 'XG', 'SHOTS']
    
    # Fallback for manglende stats
    for c in ['XG', 'SHOTS']:
        if c not in df.columns: df[c] = 0.0

    disp = df[final_cols].copy()
    disp.columns = ['Dato', 'Rd.', 'Kamp', 'Mål', 'xG', 'Skud']

    st.dataframe(disp, use_container_width=True, hide_index=True)
