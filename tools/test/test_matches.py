import streamlit as st
import pandas as pd

def vis_side(df_raw=None):
    # 1. Hent dataen råt
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return
        
    dp = st.session_state["dp"]
    df_matches = dp.get("opta_matches", pd.DataFrame())

    st.title("🛰️ Rå Data-forbindelse")

    # 2. Vis hvad vi har i kassen overhovedet
    if df_matches is None or df_matches.empty:
        st.error("LORTET ER TOMT: Snowflake returnerede 0 rækker.")
        st.info("Dette betyder at fejlen ligger i din SQL Query eller i din database-forbindelse.")
        return

    # 3. Tving kolonnenavne til UPPER så vi kan læse dem
    df_matches.columns = [c.upper() for c in df_matches.columns]

    st.success(f"HUL IGENNEM! Vi har fundet {len(df_matches)} rækker.")

    # 4. Smid det hele ind i en tabel - ingen dikkedarer
    st.write("Her er de første 100 rækker vi fandt:")
    st.dataframe(df_matches.head(100))

    # 5. En lille hjælper til at finde ud af, hvad kolonnerne hedder
    if st.checkbox("Vis alle kolonnenavne"):
        st.write(list(df_matches.columns))
