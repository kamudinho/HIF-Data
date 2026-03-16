import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data")

    # 1. Hent matches FØRST
    matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {}) # Hent name_map så vi kan se navne
    
    if matches.empty:
        st.warning("Ingen kampe fundet.")
        return

    # 2. Sorter efter dato (nyeste først) - nu virker det, da 'matches' findes
    if 'MATCH_DATE_FULL' in matches.columns:
        matches['MATCH_DATE_FULL'] = pd.to_datetime(matches['MATCH_DATE_FULL'])
        matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)
    
    # --- Tjek hvilke kampe der findes i metadata-tabellen ---
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    
    with st.spinner("Tjekker dækning..."):
        # Vi stripper 'g' direkte i SQL for at matche din covered_uuids logik
        covered_matches_df = conn.query("SELECT DISTINCT \"MATCH_OPTAUUID\" FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA")
        covered_uuids = set(covered_matches_df["MATCH_OPTAUUID"].tolist()) if not covered_matches_df.empty else set()

    def get_label(row):
        uid = str(row['MATCH_OPTAUUID'])
        if uid.startswith('g'): uid = uid[1:]
        icon = "📈" if uid in covered_uuids else "❌"
        return f"{icon} {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}"

    match_labels = matches.apply(get_label, axis=1)
    selected_idx = st.selectbox("Vælg kamp (📈 = Data tilgængelig)", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    
    selected_match = matches.iloc[selected_idx]
    match_uuid = selected_match['MATCH_OPTAUUID']
    
    if st.button("Hent fysisk data"):
        with st.spinner("Henter data..."):
            status = analyse_load.check_physical_data_availability(match_uuid)
            
            if status["rows"] > 0:
                full_dp = analyse_load.get_analysis_package(hif_only=False, match_uuid=match_uuid)
                df_fys = full_dp["fysisk_data"]
                
                # --- NAVNE MAPPING ---
                # Finder kolonnen med spiller ID (typisk PLAYER_OPTAUUID eller lign)
                id_col = next((c for c in df_fys.columns if 'OPTAUUID' in c.upper()), None)
                if id_col:
                    df_fys['SPILLER'] = df_fys[id_col].astype(str).str.lower().map(name_map).fillna(df_fys[id_col])
                    # Flyt spiller til første kolonne
                    cols = ['SPILLER'] + [c for c in df_fys.columns if c != 'SPILLER']
                    df_fys = df_fys[cols]

                st.success(f"Viser data for {selected_match['CONTESTANTHOME_NAME']} vs {selected_match['CONTESTANTAWAY_NAME']}")
                st.dataframe(df_fys, use_container_width=True)
            else:
                st.error(f"❌ Data findes ikke i systemet endnu.")
                st.info(f"""
                **Teknisk status for denne kamp:**
                * **Metadata:** {"Fundet ✅" if status['meta'] else "Ikke fundet ❌"}
                * **SSIID:** `{status.get('ss_id', 'Mangler')}`
                * **Rækker i F53A-tabellen:** `{status['rows']}`
                """)
