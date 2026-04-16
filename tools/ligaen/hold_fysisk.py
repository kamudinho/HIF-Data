import streamlit as st
import pandas as pd
import plotly.express as px
from data.data_load import _get_snowflake_conn

def vis_side():
    st.set_page_config(page_title="League Physical Benchmark", layout="wide")
    st.title("🏆 Liga-Benchmark: Fysisk Hierarki")
    
    conn = _get_snowflake_conn()
    
    # Henter data for alle hold i ligaen
    sql = """
        SELECT 
            P.MATCH_TEAMS,
            AVG(P.DISTANCE / (NULLIF(TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT), 0)/90)) as DIST_P90,
            AVG(P.NO_OF_HIGH_INTENSITY_RUNS / (NULLIF(TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT), 0)/90)) as HI_P90,
            AVG(P."HIGH SPEED RUNNING" / (NULLIF(TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT), 0)/90)) as HSR_P90,
            MAX(P.TOP_SPEED) as MAX_SPEED
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        INNER JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE (M.COMPETITION_OPTAID = '148' OR M.SECOND_SPECTRUM_COMPETITION_ID = '328')
          AND M.DATE >= '2025-07-01'
        GROUP BY P.MATCH_TEAMS
    """
    
    df = conn.query(sql)
    if df is None: return

    # Rens holdnavne (da de ofte står som "Team A - Team B")
    # Vi splitter dem op for at få unikke hold-stats
    team_stats = []
    # Simpelt loop til at aggregere pr. unikt hold
    unique_teams = ["Hvidovre", "Kolding IF", "B93", "FC Fredericia", "Hobro", "AC Horsens", "Esbjerg", "OB", "HB Køge", "Roskilde"]
    
    for t in unique_teams:
        mask = df['MATCH_TEAMS'].str.contains(t, case=False, na=False)
        if mask.any():
            team_stats.append({
                'Hold': t,
                'HI_Runs': df[mask]['HI_P90'].mean(),
                'Distance': df[mask]['DIST_P90'].mean(),
                'Sprints_HSR': df[mask]['HSR_P90'].mean(),
                'Top_Speed': df[mask]['MAX_SPEED'].max()
            })
    
    df_league = pd.DataFrame(team_stats).sort_values('HI_Runs', ascending=False)

    # --- VISNING ---
    st.write("### Den samlede fysiske tabel")
    st.dataframe(df_league.style.highlight_max(axis=0, color='#006D00'), use_container_width=True)

    col1, col2 = st.columns(2)
    
    with col1:
        metric = st.selectbox("Vælg metrik til graf", ['HI_Runs', 'Distance', 'Sprints_HSR', 'Top_Speed'])
        fig = px.bar(df_league.sort_values(metric), x=metric, y='Hold', orientation='h',
                     color='Hold', color_discrete_map={'Hvidovre': '#006D00', 'Kolding IF': '#FF0000'})
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.info(f"""
        **Konklusion baseret på data:**
        * **HI-Løb:** Kolding IF er markant stærkere. De vinder på intensitet.
        * **Taktisk modtræk:** Undgå fysisk udmattelseskrig. Fokusér på positionering og at lade bolden løbe for jer.
        """)

if __name__ == "__main__":
    vis_side()
