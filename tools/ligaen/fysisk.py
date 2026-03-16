import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    st.title("Betinia Ligaen | Fysisk Data")

    @st.cache_data(ttl=600)
    def debug_data():
        # Vi henter rå data uden joins for at se hvad der foregår
        meta = conn.query(f"SELECT STARTTIME, MATCH_SSIID, HOME_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' LIMIT 5")
        phys = conn.query("SELECT MATCH_SSIID, MATCH_TEAMS, PLAYER_NAME FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS LIMIT 5")
        return meta, phys

    df_meta, df_phys = debug_data()

    # --- DEBUG SEKTION (Kun synlig for dig nu) ---
    with st.expander("Inspektion af rå data (Hvorfor matcher de ikke?)"):
        col1, col2 = st.columns(2)
        col1.write("Eksempel på SSIID fra Metadata:")
        col1.code(df_meta['MATCH_SSIID'].iloc[0] if not df_meta.empty else "Ingen data")
        
        col2.write("Eksempel på SSIID fra Fysisk tabel:")
        col2.code(df_phys['MATCH_SSIID'].iloc[0] if not df_phys.empty else "Ingen data")
        
        st.write("Unikke holdnavne fundet i MATCH_TEAMS:")
        if not df_phys.empty:
            st.code(df_phys['MATCH_TEAMS'].unique().tolist())

    # --- DEN REPAREREDE LOGIK ---
    # 1. Vi fjerner whitespace fra ID'er for en sikkerheds skyld
    df_phys['MATCH_SSIID'] = df_phys['MATCH_SSIID'].astype(str).str.strip()
    
    # 2. Vi leder efter 'Hvidovre' (eller hvad holdet nu hedder i MATCH_TEAMS)
    # Hvis 'Hvidovre' ikke findes, prøver vi at se om vi bare kan bruge SSIID matchet
    df_hif_players = df_phys[df_phys['MATCH_TEAMS'].str.contains('Hvidovre', case=False, na=False)].copy()

    if df_hif_players.empty:
        st.warning("Kunne ikke finde 'Hvidovre' i MATCH_TEAMS. Viser alle data for at du kan identificere navnet.")
        st.dataframe(df_phys.head(10))
    else:
        st.success(f"Fundet {len(df_hif_players)} rækker for Hvidovre!")
        # Herfra kan vi køre den normale visning...
        st.dataframe(df_hif_players.head(10))
