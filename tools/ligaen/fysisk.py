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
    if st.button("Kør Rå SQL check (Metadata mapping)"):
        from data.data_load import _get_snowflake_conn
        conn = _get_snowflake_conn()
        
        # TEST 1: Findes kampen overhovedet?
        st.write(f"Søger efter: `{match_uuid}`")
        check_sql = f'SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA WHERE "MATCH_OPTAUUID" = \'{match_uuid}\''
        check_res = conn.query(check_sql)
        
        if check_res is not None and not check_res.empty:
            st.success("✅ FUNDET! Metadata findes.")
            st.write(check_res)
        else:
            st.error("❌ IKKE FUNDET i metadata.")
            
            # TEST 2: Hvad findes der så? (De 5 nyeste rækker i metadata)
            st.write("### De 5 første rækker i metadata-tabellen:")
            raw_data = conn.query('SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA LIMIT 5')
            st.dataframe(raw_data)
            
            if not raw_data.empty:
                st.write("Sammenlign dit valgte UUID med dem i tabellen ovenfor. Er der forskel i formatet?")
                
                # Kør et direkte check hvis det fejler
                if st.button("Kør rå SQL check (Metadata mapping)"):
                    from data.data_load import _get_snowflake_conn
                    conn = _get_snowflake_conn()
                    check_sql = f'SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA WHERE "MATCH_OPTAUUID" = \'{match_uuid}\''
                    check_res = conn.query(check_sql)
                    st.write("Resultat af råt metadata-tjek:", check_res)
