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
    if st.button("Hvilke ID'er findes i F53A?"):
        # Vi henter bare de 5 første unikke ID'er fra den fysiske tabel
        sample_ids = conn.query('SELECT DISTINCT "MATCH_SSIID" FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER LIMIT 5')
        st.write("### Eksempler på SSIID'er der FAKTISK har data:")
        st.dataframe(sample_ids)
        
        st.write("---")
        st.write(f"**Dit valgte kamps ID:** `{match_uuid}`")
