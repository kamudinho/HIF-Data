import streamlit as st
import pandas as pd

# Dine gemte værdier
HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn):
    st.title("Hvidovre IF - Kampoversigt 25/26")
    st.caption("Data fra Second Spectrum via Axis")

    @st.cache_data(ttl=600)
    def get_all_matches():
        # Query baseret på dit specifikke dump
        query = f"""
        SELECT 
            DATE,
            HOME_OPTAUUID,
            AWAY_OPTAUUID,
            MATCH_SSIID,
            MATCH_OPTAUUID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE (HOME_OPTAUUID = '{HIF_OPTA_UUID}' OR AWAY_OPTAUUID = '{HIF_OPTA_UUID}')
          AND COMPETITION_OPTAUUID = '6ifaeunfdelecgticvxanikzu'
        ORDER BY DATE DESC
        """
        return conn.query(query)

    df = get_all_matches()

    if df.empty:
        st.warning("Ingen kampe fundet.")
        return

    # Formatering til oversigten
    df['Rolle'] = df.apply(lambda x: "Hjemme" if x['HOME_OPTAUUID'] == HIF_OPTA_UUID else "Ude", axis=1)
    
    # Vi rydder op i visningen
    df_display = df[['DATE', 'Rolle', 'MATCH_SSIID']].copy()
    df_display.columns = ['Dato', 'HIF Rolle', 'Second Spectrum ID']

    # Visning i appen
    st.dataframe(
        df_display, 
        use_container_width=True, 
        hide_index=True
    )

    # Mulighed for at vælge en kamp til senere brug
    valgt_ssiid = st.selectbox("Vælg en kamp for at kopiere SSIID:", df['MATCH_SSIID'])
    st.code(valgt_ssiid)

# Husk at kalde funktionen i din main app
# vis_kamp_oversigt(conn)
