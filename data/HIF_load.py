import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries
from data.utils.team_mapping import TOURNAMENTCALENDAR_NAME, COMPETITION_WYID

def load_scouting_reports():
    """Indlæser dine lokale scout-rapporter fra CSV."""
    try:
        # Vi indlæser din scouting_db.csv som du sendte tidligere
        df = pd.read_csv('data/scouting_db.csv')
        # Rens kolonnenavne for mellemrum og gør dem til store bogstaver for match
        df.columns = [c.strip().upper() for c in df.columns]
        
        # Omdan dato til datetime med det samme for tidslinjer
        if 'DATO' in df.columns:
            df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Fejl ved indlæsning af scouting_db.csv: {e}")
        return pd.DataFrame()

def get_scouting_package():
    """Hovedfunktionen der samler alt data til din Database-visning."""
    conn = _get_snowflake_conn()
    
    # Hent filtre fra din team_mapping
    season_f = str(TOURNAMENTCALENDAR_NAME)
    comp_f = COMPETITION_WYID # f.eks. (328,)
    
    wy_queries = get_wy_queries(comp_f, season_f)
    
    df_sql_players = pd.DataFrame()
    df_career = pd.DataFrame()
    
    # 1. Hent data fra Snowflake
    if conn:
        try:
            # Hent aktive spillere i ligaen (til billeder og mapping)
            df_sql_players = conn.query(wy_queries.get("players"))
            # Hent karriere-statistik (til Tab 4 i din profil-dialog)
            df_career = conn.query(wy_queries.get("player_career"))
            
            # Standardiser kolonner til UPPERCASE
            for df in [df_sql_players, df_career]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
        except Exception as e:
            st.sidebar.warning(f"Kunne ikke hente SQL data: {str(e)[:50]}")

    # 2. Hent lokale data
    df_local_reports = load_scouting_reports()
    df_csv_players = load_local_players() # Din players.csv som backup

    # 3. Returner pakken i det format din vis_side forventer
    return {
        "scout_reports": df_local_reports,  # Sendes som scout_df
        "players": df_sql_players if not df_sql_players.empty else df_csv_players, # Sendes som spillere_df
        "stats": pd.DataFrame(),           # Pladsholder til stats_df
        "career": df_career                # Sendes som career_df
    }
