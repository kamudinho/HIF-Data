import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data")
    
    # 1. VISUALISER DE INDKOMMENDE DATA (DEBUG)
    with st.expander("🔍 Debug: Match Selection"):
        matches = dp["matches"]
        st.write("Antal kampe fundet:", len(matches))
        if not matches.empty:
            st.write("Kolonner i matches:", matches.columns.tolist())

    # Lav en selector baseret på de kampe der findes i dp["matches"]
    match_list = matches['CONTESTANTHOME_NAME'] + " vs " + matches['CONTESTANTAWAY_NAME']
    selected_idx = st.selectbox("Vælg kamp", range(len(match_list)), format_func=lambda x: match_list.iloc[x])
    
    match_uuid = matches.iloc[selected_idx]['MATCH_OPTAUUID']
    
    # VIS VALGT UUID
    st.info(f"Valgt Opta UUID: `{match_uuid}`")
    
    # Gen-hent pakken med det specifikke match_uuid for at få fysisk data
    if st.button("Hent fysisk data for kamp"):
        with st.spinner("Henter data fra Second Spectrum..."):
            # Her kalder vi din analyse_load funktion
            full_dp = analyse_load.get_analysis_package(hif_only=False, match_uuid=match_uuid)
            df_fys = full_dp["fysisk_data"]
            
            # DEBUG AF RESULTATET
            if not df_fys.empty:
                st.success(f"Succes! Hentede {len(df_fys)} rækker.")
                
                # Metadata check - findes koblingen?
                st.write("### Smagsprøve på data")
                st.dataframe(df_fys.head(10))
                
                # Mulighed for at se alle kolonner (Physical tabellen har mange!)
                if st.checkbox("Vis alle kolonnenavne"):
                    st.write(df_fys.columns.tolist())
            else:
                st.error("❌ Ingen data returneret.")
                st.write("""
                **Mulige årsager:**
                1. `MATCH_OPTAUUID` findes ikke i `SECONDSPECTRUM_GAME_METADATA`.
                2. `MATCH_SSIID` i metadata peger på et ID, der ikke findes i `SECONDSPECTRUM_F53A_GAME_PLAYER`.
                3. Snowflake kolonnenavne kræver "gåseøjne" (Double Quotes).
                """)
                
                # Kør et direkte check hvis det fejler
                if st.button("Kør rå SQL check (Metadata mapping)"):
                    from data.data_load import _get_snowflake_conn
                    conn = _get_snowflake_conn()
                    check_sql = f'SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA WHERE "MATCH_OPTAUUID" = \'{match_uuid}\''
                    check_res = conn.query(check_sql)
                    st.write("Resultat af råt metadata-tjek:", check_res)
