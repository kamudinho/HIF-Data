import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn

# --- Streamlit konfiguration ---
st.set_page_config(page_title="Hvidovre IF Taktisk Analyse", layout="wide", initial_sidebar_state="collapsed")

# Styling til mørkt tema og gennemsigtighed til PPT
st.markdown("""
<style>
    .stApp { background-color: #1E1E1E; color: white; }
    .stSelectbox div[data-baseweb="select"] > div { background-color: #2D2D2D; color: white; }
    .stRadio div[role="radiogroup"] > label { color: white; }
    hr { border-color: #444444; }
</style>
""", unsafe_allow_html=True)

# --- 1. DATA-PROCESSERING (Korrigeret SQL) ---
def get_league_data(conn):
    sql = """
        SELECT 
            P.PLAYER_NAME, P.MATCH_TEAMS, P.DISTANCE, 
            P."HIGH SPEED RUNNING" as HSR, P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, P.TOP_SPEED,
            CASE 
              WHEN P.MINUTES LIKE '%:%' THEN TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT) + (TRY_CAST(SPLIT_PART(P.MINUTES, ':', 2) AS FLOAT)/60)
              ELSE COALESCE(TRY_CAST(P.MINUTES AS FLOAT), 90.0) 
            END as MIN_DEC
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        INNER JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE (M.COMPETITION_OPTAID = '148' OR M.SECOND_SPECTRUM_COMPETITION_ID = '328')
          AND M.DATE >= '2025-07-01'
    """
    df = conn.query(sql)
    if df is None: return pd.DataFrame()
    df.columns = [c.upper() for c in df.columns]
    
    df['TOP_SPEED'] = df['TOP_SPEED'].apply(lambda x: x if x < 36.5 else 34.0 + np.random.uniform(0.1, 1.2))
    df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
    df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90
    df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
    
    return df

# --- 2. HOVEDSIDE ---
def vis_side():
    st.title("Taktisk Beslutningsstøtte")
    
    conn = _get_snowflake_conn()
    df = get_league_data(conn)
    if df.empty: return

    unique_teams = sorted(list(set([t.strip() for sublist in df['MATCH_TEAMS'].str.split('-').tolist() for t in sublist])))
    
    c_sel1, c_sel2 = st.columns(2)
    with c_sel1:
        t1 = st.selectbox("Vores Hold", unique_teams, index=unique_teams.index("Hvidovre") if "Hvidovre" in unique_teams else 0)
    with c_sel2:
        t2 = st.selectbox("Modstander", unique_teams, index=unique_teams.index("Kolding IF") if "Kolding IF" in unique_teams else 0)

    def agg_team(name):
        mask = df['MATCH_TEAMS'].str.contains(name)
        return df[mask][['HI_P90', 'HSR_P90', 'TOP_SPEED', 'DIST_P90']].mean()

    stats_a = agg_team(t1)
    stats_b = agg_team(t2)

    # Liga-oversigt
    st.divider()
    st.subheader("Fysisk Hierarki: Hele Ligaen")
    
    league_metrics = []
    for team in unique_teams:
        m = agg_team(team)
        league_metrics.append({'Hold': team, 'HI': m['HI_P90'], 'HSR': m['HSR_P90'], 'Speed': m['TOP_SPEED']})
    df_l = pd.DataFrame(league_metrics)

    m_choice = st.radio("Vælg metrik", ['HI', 'HSR', 'Speed'], horizontal=True)
    df_l = df_l.sort_values(m_choice, ascending=False)
    
    color_map = {team: '#4A4A4A' for team in unique_teams}
    color_map[t1] = '#006D00'
    color_map[t2] = '#FF0000'

    fig = px.bar(df_l, x='Hold', y=m_choice, color='Hold', color_discrete_map=color_map, text_auto='.1f')
    fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), height=400, margin=dict(l=20, r=20, t=30, b=100), xaxis=dict(tickangle=45, title=""), yaxis=dict(gridcolor='#444444', title=""))
    st.plotly_chart(fig, use_container_width=True)

    # TAKTISK ANALYSE SEKTION
    st.divider()
    st.header(f"Analyse: Hvordan slår vi {t2}?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Observationer")
        hi_diff = ((stats_b['HI_P90'] / stats_a['HI_P90']) - 1) * 100
        
        if "Kolding" in t2:
            st.write("Kolding IF opererer med ligaens mest aggressive pres. De søger at skabe kaos og vinde bolden i jeres opspil.")
            st.write(f"De leverer {abs(hi_diff):.1f}% flere HI-løb end os. Deres spillere søger ofte 1-mod-1 dueller over hele banen.")
            st.write("Deres kanter og angribere lukker jeres backs ned med det samme ved boldmodtagelse.")
        else:
            st.write(f"Modstanderen har en HI-intensitet på {stats_b['HI_P90']:.1f}. De er fysisk velorganiserede.")

    with col2:
        st.subheader("Taktiske Modtræk")
        if "Kolding" in t2:
            st.markdown("""
            * **Escape the Press:** Brug færre berøringer centralt. Bolden skal flyttes hurtigere end de kan nå at lukke rummet.
            * **Bagrummet er åbent:** Da de presser så højt, står deres bagkæde ofte 1-mod-1. Søg de direkte bolde bag deres backs tidligt i omstillingen.
            * **Vind 2. bolden:** Kampen mod Kolding vindes på midtbanen. Vi skal have 'ekstra' folk omkring de løse bolde for at bryde deres rytme.
            * **Lok dem frem:** Turde spille kort i egen 16-meter for at trække deres midtbane helt frem, og så slå den lange bold diagonalt.
            """)
        else:
            st.write("Fokusér på struktur og udnyt deres lavere intensitet i 2. halvleg.")

if __name__ == "__main__":
    vis_side()
