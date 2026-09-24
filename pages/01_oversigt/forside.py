# pages/01_oversigt/forside.py
import streamlit as st
import pandas as pd
from data.utils.data.sql.teams import (
    hent_hurtig_stilling,
    hent_hold_formkurve
)

def vis_side():
    season_name = "2026/2027"
    calendar_uuid = '2mb332vncy4450vu14paj8844'  

    st.markdown(f"### Holdets Nøgletal - Sæson {season_name}")
    
    # Hent stillingstabellen fra Snowflake
    df_stilling = hent_hurtig_stilling(calendar_uuid)

    # Find Hvidovres data direkte fra stillingstabellen (sindssygt stabilt)
    hvidovre_row = pd.Series(dtype=object)
    hvidovre_optauuid = None
    
    point = 0
    kampe_spillet = 0
    maal_for = 0
    maal_imod = 0

    if df_stilling is not None and not df_stilling.empty:
        hv_row_st = df_stilling[df_stilling['HOLD'].str.contains("Hvidovre", case=False, na=False)]
        if not hv_row_st.empty:
            hvidovre_row = hv_row_st.iloc[0]
            hvidovre_optauuid = hvidovre_row.get('TEAM_ID')
            point = int(hvidovre_row.get('P', 0))
            kampe_spillet = int(hvidovre_row.get('K', 0))
            maal_for = int(hvidovre_row.get('GF', 0))
            maal_imod = int(hvidovre_row.get('GA', 0))

    # --- 1. SEKTION: HOVEDOVERBLIK & NØGLEMETAL (KPI KORT) ---
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(label="Kampe Spillet", value=str(kampe_spillet))
    with col2:
        st.metric(label="Point", value=str(point))
    with col3:
        st.metric(label="Målscore", value=f"{maal_for} - {maal_imod}")
    with col4:
        st.metric(label="Mål snit (for)", value=f"{(maal_for / kampe_spillet if kampe_spillet > 0 else 0):.2f}", delta="pr. kamp")
    with col5:
        st.metric(label="Mål snit (imod)", value=f"{(maal_imod / kampe_spillet if kampe_spillet > 0 else 0):.2f}", delta="pr. kamp")

    st.divider()

    # --- 2. SEKTION: SENESTE RESULTATER ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Seneste kampe")
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
        st.markdown("#### Hvidovre IF Status")
        if not hvidovre_row.empty:
            st.success(f"Hvidovre IF er placeret som nr. **{int(hvidovre_row.get('POSITION', 0))}** i NordicBet Ligaen med **{point} point** efter {kampe_spillet} kampe.")
        else:
            st.info("Afventer turneringsdata...")

    st.divider()

    # --- 3. SEKTION: TURNERINGSSTILLING ---
    st.markdown("### Stilling i Ligaen")
    if df_stilling is not None and not df_stilling.empty:
        st.dataframe(df_stilling[['POSITION', 'HOLD', 'K', 'V', 'U', 'T', 'MF', 'P']], use_container_width=True, hide_index=True)
    else:
        st.info("Kunne ikke indhente stillingstabellen.")
