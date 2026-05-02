import streamlit as st
import pandas as pd

def vis_side(conn):
    st.title("🛠 Datakatalog & Dokumentation")

    # --- ORDBOG TIL STAT_TYPE ---
    stat_forklaringer = {
        "minsPlayed": "Antal spillede minutter.",
        "yellowCard": "Gule kort.",
        "redCard": "Rødt kort.",
        "touches": "Antal berøringer i alt.",
        "touchesInOppBox": "Berøringer i modstanderens felt.",
        "goals": "Antal scorede mål i alt.",
        "goalAssist": "Målgivende aflevering (Assist).",
        "totalScoringAtt": "Samlede afslutninger (skud i alt).",
        "expectedGoals": "xG - Samlet forventede mål.",
        "expectedAssists": "xA - Forventede assists.",
        # ... tilføj de øvrige fra listen herover
    }

    # 1. Forbindelses-status (Hurtigt overblik)
    try:
        status = conn.query("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE()")
        st.caption(f"Forbundet som: {status.iloc[0,0]} ({status.iloc[0,1]})")
    except:
        pass

    # Lav faner
    tab_struktur, tab_stats, tab_kode = st.tabs(["📋 Tabelstruktur", "📊 Stat_Type Forklaringer", "💻 Kode-eksempel"])

    # --- FANE 1: TABELSTRUKTUR ---
    with tab_struktur:
        tabeller = ['OPTA_MATCHEXPECTEDGOALS', 'OPTA_MATCHSTATS', 'OPTA_PLAYERS']
        valgt_tabel = st.selectbox("Vælg tabel for at se kolonner:", tabeller)
        
        if valgt_tabel:
            query_cols = f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM KLUB_HVIDOVREIF.INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{valgt_tabel}' AND TABLE_SCHEMA = 'AXIS'
                ORDER BY ORDINAL_POSITION
            """
            df_cols = conn.query(query_cols)
            st.dataframe(df_cols, use_container_width=True, hide_index=True)

    # --- FANE 2: STAT_TYPE FORKLARINGER ---
    with tab_stats:
        st.subheader("Oversættelse af Opta Stats")
        # Vi henter de unikke typer fra de to primære stat-tabeller
        try:
            st_query = "SELECT DISTINCT STAT_TYPE FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHSTATS"
            df_st = conn.query(st_query)
            df_st['Forklaring'] = df_st['STAT_TYPE'].map(stat_forklaringer).fillna("⚠️ Mangler forklaring")
            
            st.dataframe(df_st.sort_values('STAT_TYPE'), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Kunne ikke hente stat-typer: {e}")

    # --- FANE 3: KODE-EKSEMPEL ---
    with tab_kode:
        st.subheader("Sådan bruger du STAT_TYPE i din kode")
        st.info("Brug denne metode når du skal trække specifikke tal ud til spiller- eller kampsider.")
        
        kode_eksempel = """
# Eksempel på hvordan du filtrerer xG og Assists i din data-load
def get_player_performance(conn, player_uuid):
    query = f'''
        SELECT 
            STAT_TYPE, 
            STAT_VALUE 
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHSTATS
        WHERE PLAYER_OPTAUUID = '{player_uuid}'
        AND STAT_TYPE IN ('expectedGoals', 'goalAssist', 'touchesInOppBox')
    '''
    df = conn.query(query)
    
    # Map forklaringerne på i koden
    ordbog = {
        'expectedGoals': 'xG',
        'goalAssist': 'Assists',
        'touchesInOppBox': 'Felt-aktioner'
    }
    df['Label'] = df['STAT_TYPE'].map(ordbog)
    return df
        """
        st.code(kode_eksempel, language='python')
