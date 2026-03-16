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
            
            if st.button("Kør Database Diagnostik"):
            from data.data_load import _get_snowflake_conn
            conn = _get_snowflake_conn()
            
            st.write("### Diagnostik af Second Spectrum Tabeller")
            
            # 1. Hvor mange rækker er der i alt?
            total_fys = conn.query("SELECT COUNT(*) FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER")
            st.write(f"Total antal rækker i F53A tabellen: `{total_fys.iloc[0,0]}`")
            
            # 2. Vis de 5 nyeste unikke SSIID'er i F53A tabellen
            st.write("### De 5 nyeste SSIID'er med FAKTISK data i F53A:")
            latest_ids = conn.query("""
                SELECT DISTINCT "MATCH_SSIID", COUNT(*) as ANTAL_RÆKKER 
                FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
                GROUP BY "MATCH_SSIID" 
                LIMIT 5
            """)
            st.dataframe(latest_ids)
