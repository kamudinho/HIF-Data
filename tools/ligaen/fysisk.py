import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data")

    # 1. Hent matches og name_map
    matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {}) 
    
    if matches.empty:
        st.warning("Ingen kampe fundet.")
        return

    # 2. Sorter efter dato (nyeste først)
    if 'MATCH_DATE_FULL' in matches.columns:
        matches['MATCH_DATE_FULL'] = pd.to_datetime(matches['MATCH_DATE_FULL'])
        matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)
    
    # --- Tjek dækning i metadata ---
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    
    with st.spinner("Tjekker dækning..."):
        # Vi henter alle OptaUUIDs fra metadata for at sætte ikoner (📈/❌)
        covered_matches_df = conn.query("SELECT DISTINCT \"MATCH_OPTAUUID\" FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA")
        covered_uuids = set(covered_matches_df["MATCH_OPTAUUID"].tolist()) if not covered_matches_df.empty else set()

    def get_label(row):
        uid = str(row['MATCH_OPTAUUID'])
        if uid.startswith('g'): uid = uid[1:]
        icon = "📈" if uid in covered_uuids else "❌"
        return f"{icon} {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}"

    # VIGTIGT: Disse skal være i samme indrykningsniveau som 'def get_label'
    match_labels = matches.apply(get_label, axis=1)
    selected_idx = st.selectbox("Vælg kamp (📈 = Data tilgængelig)", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    
    selected_match = matches.iloc[selected_idx]
    match_uuid = selected_match['MATCH_OPTAUUID']
    
    # --- Diagnostik Knap ---
    if st.button("Kør Database Diagnostik"):
        st.write("### Diagnostik af Second Spectrum Tabeller")
        
        # 1. Hvor mange rækker er der i alt i den fysiske tabel?
        total_fys = conn.query("SELECT COUNT(*) as TOTAL FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER")
        st.write(f"Total antal rækker i F53A tabellen: `{total_fys.iloc[0,0]}`")
        
        # 2. Vis de nyeste unikke SSIID'er i F53A tabellen
        st.write("### De nyeste SSIID'er med data i F53A:")
        latest_ids = conn.query("""
            SELECT "MATCH_SSIID", COUNT(*) as ANTAL_RÆKKER 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
            GROUP BY "MATCH_SSIID" 
            LIMIT 10
        """)
        st.dataframe(latest_ids)

    # --- Hent Fysisk Data Knap ---
    if st.button("Hent fysisk data for valgt kamp"):
        with st.spinner("Henter data..."):
            status = analyse_load.check_physical_data_availability(match_uuid)
            
            if status["rows"] > 0:
                full_dp = analyse_load.get_analysis_package(hif_only=False, match_uuid=match_uuid)
                df_fys = full_dp["fysisk_data"]
                st.success(f"Fundet {len(df_fys)} rækker!")
                st.dataframe(df_fys)
            else:
                st.error("❌ Metadata findes, men F53A-tabellen er tom for denne kamp.")
                st.info(f"SSIID fundet i metadata: `{status.get('ss_id')}`")
