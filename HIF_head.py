import streamlit as st
import pandas as pd
from utils.data.data_load import _get_snowflake_conn
from utils.data.sql.teams import (
    hent_hurtig_stilling,
    hent_samlet_hold_statistik,
    hent_hold_formkurve
)

DB = "KLUB_HVIDOVREIF.AXIS"

@st.cache_data(ttl=3600)
def _faar_standard_kalender_uuid():
    """Henter det første tilgængelige kalender-UUID fra databasen til visning."""
    conn = _get_snowflake_conn()
    if not conn:
        return None
    try:
        query = f"SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO LIMIT 1"
        cur = conn.cursor()
        cur.execute(query)
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    except Exception:
        return None

def vis_side():
    st.markdown("### Holdets Nøgletal - Sæson 2025/2026")
    
    calendar_uuid = _faar_standard_kalender_uuid()
    if not calendar_uuid:
        st.warning("Kunne ikke finde et aktivt turneringskalender-UUID i Snowflake.")
        return

    # Hent samlet holdstatistik og stilling
    df_stats = hent_samlet_hold_statistik(calendar_uuid)
    df_stilling = hent_hurtig_stilling(calendar_uuid)

    # Filtrér data for Hvidovre (Matcher på holdnavn eller ID)
    hvidovre_row = pd.Series()
    if df_stats is not None and not df_stats.empty:
        match_hvidovre = df_stats[df_stats['TEAM_NAME'].str.contains("Hvidovre", case=False, na=False)]
        if not match_hvidovre.empty:
            hvidovre_row = match_hvidovre.iloc[0]

    # Udtræk værdier med sikre standarder, hvis data mangler
    kampe_spillet = int(hvidovre_row.get('ACTUAL_MATCHES', 0)) if not hvidovre_row.empty else 0
    maal_for = int(hvidovre_row.get('TOTAL_GOALS', 0)) if not hvidovre_row.empty else 0
    maal_imod = int(hvidovre_row.get('TOTAL_GOALS_AGAINST', 0)) if not hvidovre_row.empty else 0
    xg_pr_kamp = float(hvidovre_row.get('XG_P90', 0.0)) if not hvidovre_row.empty else 0.0
    boldbesiddelse = float(hvidovre_row.get('AVG_POSSESSION_PCT', 0.0)) if not hvidovre_row.empty else 0.0

    # Hent point fra stillingstabellen
    point = 0
    if df_stilling is not None and not df_stilling.empty:
        hv_stilling = df_stilling[df_stilling['HOLD'].str.contains("Hvidovre", case=False, na=False)]
        if not hv_stilling.empty:
            point = int(hv_stilling.iloc[0].get('P', 0))

    # --- 1. SEKTION: HOVEDOVERBLIK & NØGLEMETAL (KPI KORT) ---
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(label="Kampe Spillet", value=str(kampe_spillet))
    with col2:
        st.metric(label="Point", value=str(point))
    with col3:
        st.metric(label="Målscore", value=f"{maal_for} - {maal_imod}")
    with col4:
        st.metric(label="Forventede Mål (xG)", value=f"{xg_pr_kamp:.2f}", delta="pr. kamp")
    with col5:
        st.metric(label="Boldbesiddelse", value=f"{boldbesiddelse:.1f}%")

    st.divider()

    # --- 2. SEKTION: SENESTE RESULTATER OG UDVIKLING ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Seneste kampe")
        # Find Hvidovres Opta UUID fra stillingstabellen for at hente formkurve
        hvidovre_optauuid = None
        if df_stilling is not None and not df_stilling.empty:
            hv_row_st = df_stilling[df_stilling['HOLD'].str.contains("Hvidovre", case=False, na=False)]
            if not hv_row_st.empty:
                hvidovre_optauuid = hv_row_st.iloc[0].get('TEAM_ID')

        if hvidovre_optauuid:
            df_form = hent_hold_formkurve(calendar_uuid, hvidovre_optauuid, limit=5)
            if df_form is not None and not df_form.empty:
                recent_matches = pd.DataFrame({
                    "Kamp": df_form['CONTESTANTHOME_NAME'] + " - " + df_form['CONTESTANTAWAY_NAME'],
                    "Resultat": df_form['TOTAL_HOME_SCORE'].astype(str) + " - " + df_form['TOTAL_AWAY_SCORE'].astype(str),
                    "Form": df_form['RESULTAT']
                })
                st.dataframe(recent_matches, use_container_width=True, hide_index=True)
            else:
                st.info("Ingen formkurve-data fundet endnu.")
        else:
            st.info("Hvidovre ID ikke fundet i turneringen.")

    with col_right:
        st.markdown("#### Taktiske Nøgletal (Gennemsnit)")
        if not hvidovre_row.empty:
            tactical_stats = pd.DataFrame({
                "Parameter": ["Afslutninger pr. kamp", "Skud på mål pr. kamp", "Berøringer i felt pr. kamp", "Afleveringer pr. kamp", "Gule kort pr. kamp"],
                "Værdi": [
                    f"{float(hvidovre_row.get('SHOTS_P90', 0)):.1f}",
                    f"{float(hvidovre_row.get('ON_TARGET_SHOTS_P90', 0)):.1f}",
                    f"{float(hvidovre_row.get('TOUCHES_IN_BOX_P90', 0)):.1f}",
                    f"{float(hvidovre_row.get('PASSES_P90', 0)):.1f}",
                    f"{float(hvidovre_row.get('YELLOW_CARDS_P90', 0)):.1f}"
                ]
            })
            st.dataframe(tactical_stats, use_container_width=True, hide_index=True)
        else:
            st.info("Ingen taktisk data tilgængelig.")

    st.divider()

    # --- 3. SEKTION: TURNERINGSSTILLING ---
    st.markdown("### Stilling i Ligaen")
    if df_stilling is not None and not df_stilling.empty:
        st.dataframe(df_stilling[['POSITION', 'HOLD', 'K', 'V', 'U', 'T', 'MF', 'P']], use_container_width=True, hide_index=True)
    else:
        st.info("Kunne ikke indhente stillingstabellen.")
