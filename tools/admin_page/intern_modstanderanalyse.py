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

# --- 1. DATA-PROCESSERING ---
def get_league_data(conn):
    sql = """
        SELECT 
            P.PLAYER_NAME, P.MATCH_TEAMS, P.DISTANCE, 
            P."HIGH SPEED RUNNING" as HSR, P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, P.TOP_SPEED,
            P.DISTANCE_IN_POSSESSION as DIST_POSS, P.DISTANCE_OUT_OF_POSSESSION as DIST_OUT_POSS,
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
    # Forholdet mellem arbejde med og uden bold
    df['WORK_RATIO'] = df['DIST_OUT_POSS'] / df['DIST_POSS'].replace(0, 1)
    
    return df

# --- 2. TAKTISK VURDERINGSMOTOR (Med og uden bold) ---
def get_tactical_breakdown(stats_b, team_name):
    analysis = []
    
    # Analyse af spillestil baseret på Work Ratio (Uden bold vs Med bold)
    if stats_b['WORK_RATIO'] > 1.2:
        style = "Aggressivt Pres-hold"
        weakness = "Efterlader store rum bag midtbanen ved fejlslagent pres."
        solution = "Hurtige vertikale vendinger. Spil over deres første pres."
    else:
        style = "Besiddelsesorienteret / Kompakt"
        weakness = "Sårbar over for hurtige omstillinger ved boldtab."
        solution = "Tålmodighed i opbygningen. Lok dem ud af deres struktur."

    analysis.append(f"Profil: {team_name} optræder som et {style}.")
    analysis.append(f"Svaghed: {weakness}")
    analysis.append(f"Modtræk: {solution}")
    
    return analysis

# --- 3. HOVEDSIDE ---
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
        return df[mask][['HI_P90', 'HSR_P90', 'TOP_SPEED', 'WORK_RATIO', 'DIST_POSS', 'DIST_OUT_POSS']].mean()

    stats_a = agg_team(t1)
    stats_b = agg_team(t2)

    # 1. Graf: Fysisk Hierarki
    st.divider()
    st.subheader("Fysisk Hierarki: Hele Ligaen")
    
    league_metrics = []
    for team in unique_teams:
        m = agg_team(team)
        league_metrics.append({'Hold': team, 'HI': m['HI_P90'], 'WorkRatio': m['WORK_RATIO'], 'Speed': m['TOP_SPEED']})
    df_l = pd.DataFrame(league_metrics)

    m_choice = st.radio("Vælg metrik", ['HI', 'WorkRatio', 'Speed'], horizontal=True)
    df_l = df_l.sort_values(m_choice, ascending=False)
    
    color_map = {team: '#4A4A4A' for team in unique_teams}
    color_map[t1] = '#006D00'
    color_map[t2] = '#FF0000'

    fig = px.bar(df_l, x='Hold', y=m_choice, color='Hold', color_discrete_map=color_map, text_auto='.2f')
    fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), height=400, margin=dict(l=20, r=20, t=30, b=100), xaxis=dict(tickangle=45, title=""), yaxis=dict(gridcolor='#444444', title=""))
    st.plotly_chart(fig, use_container_width=True)

    # 2. Sektion: Taktisk vurdering (Spillestil og Modtræk)
    st.divider()
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader(f"Vurdering af {t2}")
        tactical_logic = get_tactical_breakdown(stats_b, t2)
        for line in tactical_logic:
            st.write(f"- {line}")
            
        st.write(f"**Arbejde uden bold:** {stats_b['DIST_OUT_POSS']:.0f}m i snit")
        st.write(f"**Arbejde med bold:** {stats_b['DIST_POSS']:.0f}m i snit")

    with col_right:
        st.subheader("Sådan slår vi dem")
        hi_diff = ((stats_b['HI_P90'] / stats_a['HI_P90']) - 1) * 100
        
        if hi_diff > 10:
            st.warning(f"{t2} har {hi_diff:.1f}% højere intensitet. Vi skal undgå at blive fanget i deres preszoner.")
            st.write("Anbefaling: Brug kanterne til at strække deres pres og spil hurtigt ud af de centrale områder.")
        else:
            st.success(f"Vi matcher deres intensitet. Vi kan udfordre dem på deres egen medicin.")
            st.write("Anbefaling: Aggressiv genpres og fokus på vundet 2. bold.")

if __name__ == "__main__":
    vis_side()
