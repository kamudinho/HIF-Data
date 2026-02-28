import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(df):
    st.markdown('<h3 style="color:#cc0000;">KAMPOVERSIGT</h3>', unsafe_allow_html=True)

    # 1. TOTAL SIKRING: Hvis data mangler, stop her.
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Ingen data fundet i Snowflake.")
        return

    # Lav en kopi og tving kolonner til store bogstaver
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]

    # 2. FILTER (Dropdown)
    alle_hold = sorted(list(TEAMS.keys()))
    valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + alle_hold)

    # 3. KAMP NAVN (Robust version)
    # Vi laver kolonnen 'KAMP' ved at kigge efter kendte Opta/Wyscout felter
    if 'MATCHLABEL' in df.columns:
        df['KAMP'] = df['MATCHLABEL'].astype(str).str.split(',').str[0]
    elif 'CONTESTANTHOME_NAME' in df.columns:
        df['KAMP'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
    else:
        df['KAMP'] = "Ukendt Kamp"

    # 4. UDFØR FILTER
    if valgt_hold != "Alle hold":
        # Vi søger efter en del af navnet (f.eks. "Hvidovre") for at være sikre
        soegestreg = valgt_hold.replace(" IF", "").strip()
        f_df = df[df['KAMP'].str.contains(soegestreg, case=False, na=False)].copy()
    else:
        f_df = df.copy()

    if f_df.empty:
        st.info(f"Ingen kampe fundet for {valgt_hold}")
        return

    # 5. DATO OG MÅL (Uden apply - det er her den plejer at fejle)
    # Vi bruger .get() med default værdier for at undgå fejl
    h_mål = f_df.get('TOTAL_HOME_SCORE', f_df.get('HOME_GOALS', 0)).fillna(0).astype(int).astype(str)
    a_mål = f_df.get('TOTAL_AWAY_SCORE', f_df.get('AWAY_GOALS', 0)).fillna(0).astype(int).astype(str)
    f_df['RESULTAT'] = h_mål + " - " + a_mål

    # Dato konvertering med 'errors=coerce' så den ikke crasher ved mærkelige datoer
    dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'DATE_DT'] if c in f_df.columns), None)
    if dato_col:
        f_df['DATO_STR'] = pd.to_datetime(f_df[dato_col], errors='coerce').dt.strftime('%d-%m-%Y').fillna("-")
    else:
        f_df['DATO_STR'] = "-"

    # 6. VISNING (Vi fjerner height-beregningen midlertidigt for at teste stabilitet)
    disp = f_df[['DATO_STR', 'KAMP', 'RESULTAT']].copy()
    disp.columns = ['Dato', 'Kamp', 'Mål']

    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True
    )
