import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(df):
    st.subheader("Kampoversigt")
    
    if df is None or df.empty:
        st.warning("⚠️ Ingen data modtaget fra Snowflake (df is empty)")
        return

    # Tving alt til Store Bogstaver
    df.columns = [c.upper() for c in df.columns]
    
    # 1. VIS KOLONNER FOR AT DEBUGGE (Fjern denne linje når det virker)
    # st.write("Tilgængelige kolonner:", list(df.columns))

    # 2. LAV KAMP-NAVN (Håndter både Opta og Wyscout navne)
    if 'MATCHLABEL' in df.columns:
        df['KAMP_NAVN'] = df['MATCHLABEL']
    else:
        h = df.get('CONTESTANTHOME_NAME', df.get('HOME_TEAM_NAME', 'Hjemme'))
        a = df.get('CONTESTANTAWAY_NAME', df.get('AWAY_TEAM_NAME', 'Ude'))
        df['KAMP_NAVN'] = h.astype(str) + " - " + a.astype(str)

    # 3. FILTER
    alle_hold = sorted(list(TEAMS.keys()))
    valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + alle_hold)

    if valgt_hold != "Alle hold":
        # Vi bruger en 'case=False' og fjerner " IF" for at øge chancen for match
        renset_soegning = valgt_hold.replace(" IF", "")
        f_df = df[df['KAMP_NAVN'].str.contains(renset_soegning, case=False, na=False)].copy()
    else:
        f_df = df.copy()

    if f_df.empty:
        st.info(f"Ingen kampe fundet for '{valgt_hold}' i de hentede data.")
        return

    # 4. TABEL-KLARGØRING
    # Find dato (Opta bruger ofte MATCH_DATE_FULL)
    dato_col = 'MATCH_DATE_FULL' if 'MATCH_DATE_FULL' in f_df.columns else 'DATE'
    f_df['DATO_VIS'] = pd.to_datetime(f_df[dato_col]).dt.strftime('%d-%m-%Y')
    
    # Find mål
    h_mål = f_df.get('TOTAL_HOME_SCORE', f_df.get('HOME_GOALS', 0))
    a_mål = f_df.get('TOTAL_AWAY_SCORE', f_df.get('AWAY_GOALS', 0))
    f_df['RESULTAT'] = h_mål.astype(str) + " - " + a_mål.astype(str)

    # 5. VISNING
    disp = f_df[['DATO_VIS', 'KAMP_NAVN', 'RESULTAT']]
    st.dataframe(disp, use_container_width=True, hide_index=True, height=(len(disp)*35)+40)
