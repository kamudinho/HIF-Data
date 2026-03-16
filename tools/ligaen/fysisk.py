import streamlit as st
import data.analyse_load as analyse_load
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data")
    
    matches = dp.get("matches", pd.DataFrame())
    
    # --- NYT: Tjek hvilke kampe der findes i metadata-tabellen ---
    # Dette hjælper dig med at se hvilke kampe der OVERHOVEDET har tracking-mulighed
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    
    # Hent alle tilgængelige SSIID'er i ét hug for at optimere
    with st.spinner("Tjekker dækning..."):
        covered_matches_df = conn.query("SELECT DISTINCT \"MATCH_OPTAUUID\" FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA")
        covered_uuids = set(covered_matches_df["MATCH_OPTAUUID"].tolist()) if not covered_matches_df.empty else set()

    def get_label(row):
        # Vi fjerner 'g' for at tjekke mod metadata-listen
        uid = str(row['MATCH_OPTAUUID'])
        if uid.startswith('g'): uid = uid[1:]
        
        icon = "📈" if uid in covered_uuids else "❌"
        return f"{icon} {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}"

    match_labels = matches.apply(get_label, axis=1)
    selected_idx = st.selectbox("Vælg kamp (📈 = Data tilgængelig)", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    
    match_uuid = matches.iloc[selected_idx]['MATCH_OPTAUUID']
    
    if st.button("Hent fysisk data"):
        # Her kører din eksisterende load-logik...
        full_dp = analyse_load.get_analysis_package(hif_only=False, match_uuid=match_uuid)
        df_fys = full_dp["fysisk_data"]
        
        if not df_fys.empty:
            st.dataframe(df_fys)
        else:
            st.error("Denne kamp har ingen fysiske tracking-data i systemet (F53A).")
