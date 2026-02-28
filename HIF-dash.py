import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(df):
    # --- 1. BRANDING ---
    st.markdown("""
        <div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:15px;">
            <h3 style="color:white; margin:0; text-align:center;">KAMPOVERSIGT</h3>
        </div>
    """, unsafe_allow_html=True)

    # Tjek om df findes før vi overhovedet rører den
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("⚠️ Ingen kampdata tilgængelig.")
        return

    # Standardiser kolonner med det samme (Snowflake returnerer UPPER)
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]

    # --- 2. FORBERED KAMP-NAVN (Vigtigt for filteret) ---
    if 'MATCHLABEL' in df.columns:
        df['KAMP_NAVN'] = df['MATCHLABEL'].str.split(',').str[0]
    else:
        # Opta-specifik fallback
        h = df['CONTESTANTHOME_NAME'] if 'CONTESTANTHOME_NAME' in df.columns else "Hjemme"
        a = df['CONTESTANTAWAY_NAME'] if 'CONTESTANTAWAY_NAME' in df.columns else "Ude"
        df['KAMP_NAVN'] = h.astype(str) + " - " + a.astype(str)

    # --- 3. FILTER-SEKTION ---
    alle_hold = sorted(list(TEAMS.keys()))
    
    col1, col2 = st.columns([1, 2])
    with col1:
        # Standard: Find Hvidovre IF index hvis det findes
        hvi_idx = alle_hold.index("Hvidovre IF") + 1 if "Hvidovre IF" in alle_hold else 0
        valgt_hold = st.selectbox("Vælg dit hold", ["Alle hold"] + alle_hold, index=hvi_idx)

    # Udfør filter
    if valgt_hold != "Alle hold":
        # Vi søger bredt (f.eks. "Hvidovre" matcher både "Hvidovre IF" og "Hvidovre")
        soeg = valgt_hold.replace(" IF", "").strip()
        f_df = df[df['KAMP_NAVN'].str.contains(soeg, case=False, na=False)].copy()
    else:
        f_df = df.copy()

    if f_df.empty:
        st.info(f"Ingen kampe fundet for {valgt_hold}")
        return

    # --- 4. FORMATERING AF DATA ---
    # Dato (Opta/Wyscout fallback)
    dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'DATE_DT'] if c in f_df.columns), None)
    if dato_col:
        f_df['DATO_VIS'] = pd.to_datetime(f_df[dato_col]).dt.strftime('%d-%m-%Y')
    else:
        f_df['DATO_VIS'] = "-"

    # Resultat
    def get_res(row):
        h = row.get('TOTAL_HOME_SCORE', row.get('HOME_GOALS'))
        a = row.get('TOTAL_AWAY_SCORE', row.get('AWAY_GOALS'))
        if pd.isna(h) or pd.isna(a): return "-"
        return f"{int(h)} - {int(a)}"
    
    f_df['MÅL'] = f_df.apply(get_res, axis=1)

    # --- 5. TABELVISNING UDEN SCROLL (Fejlsikret højde) ---
    disp = f_df[['DATO_VIS', 'KAMP_NAVN', 'MÅL']].copy()
    disp.columns = ['Dato', 'Kamp', 'Mål']

    # Vi sætter en max-højde så siden ikke crasher hvis der er 1000 rækker
    calc_height = (len(disp) * 35) + 40
    final_height = min(calc_height, 1200) # Max 1200px før den får scrollbar

    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        height=final_height
    )
