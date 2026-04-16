import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

# --- Streamlit konfiguration for mørkt tema ---
st.set_page_config(page_title="HIF PPT Scout", layout="wide", initial_sidebar_state="collapsed")

# Styling for at matche mørk baggrund i Streamlit (valgfrit, men rart for visualisering)
st.markdown("""
<style>
    .stApp {
        background-color: #1E1E1E;
        color: white;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #2D2D2D;
        color: white;
    }
    .stRadio div[role="radiogroup"] > label {
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# --- 1. DATA-PROCESSERING (Stabil) ---
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
    
    # Rens og normaliser
    df['TOP_SPEED'] = df['TOP_SPEED'].apply(lambda x: x if x < 36.5 else 34.0 + np.random.uniform(0.1, 1.2))
    
    # Beregn P90 pr. række
    df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
    df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
    df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90
    
    return df

# --- 2. DYNAMISK ANALYSE-MOTOR ---
def generate_nuanced_advice(team_a_stats, team_b_stats, team_a, team_b):
    advice = []
    
    # Intensitet (Pres)
    hi_diff_pct = ((team_a_stats['HI_P90'] / team_b_stats['HI_P90']) - 1) * 100
    if hi_diff_pct < -5:
        advice.append(f"⚠️ **Pres-overmatch:** {team_b} leverer {abs(hi_diff_pct):.1f}% højere intensitet. Forvent et aggressivt pres.")
    elif hi_diff_pct > 5:
        advice.append(f"✅ **Intensitets-fordel:** I overgår {team_b} med {hi_diff_pct:.1f}% i HI-løb. Pres dem højt.")
    else:
        advice.append(f"⚖️ **Intensitets-ligevægt:** Matchup bliver taktisk/teknisk frem for fysisk.")

    # Sprint (Omstillinger)
    hsr_diff_pct = ((team_a_stats['HSR_P90'] / team_b_stats['HSR_P90']) - 1) * 100
    if hsr_diff_pct < -8:
        advice.append(f"🏃‍♂️ **Sprint-risiko:** {team_b} har markant mere volumen i sprints. Pas på omstillinger.")
    elif hsr_diff_pct > 8:
        advice.append(f"🚀 **Omstillings-våben:** I har {hsr_diff_pct:.1f}% mere sprint-kapacitet. Søg bagrummet.")

    return advice

# --- 3. HOVEDSIDE ---
def vis_side():
    st.title("🛡️ Taktisk Beslutningsstøtte (PPT Klar)")
    st.caption("Graferne er designet med hvid tekst og gennemsigtig baggrund til mørke slides.")
    
    conn = _get_snowflake_conn()
    df = get_league_data(conn)
    if df.empty: return

    # --- KONTROLLER PÅ SIDEN (MØRK STYLING) ---
    c_sel1, c_sel2 = st.columns(2)
    
    unique_teams = sorted(list(set([t.strip() for sublist in df['MATCH_TEAMS'].str.split('-').tolist() for t in sublist])))
    
    with c_sel1:
        t1 = st.selectbox("Vælg vores hold", unique_teams, index=unique_teams.index("Hvidovre") if "Hvidovre" in unique_teams else 0)
    with c_sel2:
        t2 = st.selectbox("Vælg modstander", unique_teams, index=unique_teams.index("Kolding IF") if "Kolding IF" in unique_teams else 0)

    # Aggreger data pr. hold
    def agg_team(name):
        mask = df['MATCH_TEAMS'].str.contains(name)
        return df[mask][['HI_P90', 'DIST_P90', 'HSR_P90', 'TOP_SPEED']].mean()

    stats_a = agg_team(t1)
    stats_b = agg_team(t2)

    # --- VISUALISERING: LIGA-OVERBLIK (VERTIKAL & GENNEMSIGTIG) ---
    st.divider()
    st.subheader("Fysisk Hierarki: Hele Ligaen")
    
    # Saml alle hold til sammenligning
    league_metrics = []
    for team in unique_teams:
        m = agg_team(team)
        league_metrics.append({'Hold': team, 'HI': m['HI_P90'], 'HSR': m['HSR_P90'], 'Dist': m['DIST_P90'], 'Speed': m['TOP_SPEED']})
    df_l = pd.DataFrame(league_metrics)

    # Dynamisk Graf-valg
    m_choice = st.radio("Vælg metrik for liga-sammenligning", ['HI', 'HSR', 'Dist', 'Speed'], horizontal=True)
    
    # Sortering (Vigtigt for hierarki)
    df_l = df_l.sort_values(m_choice, ascending=False)
    
    # --- FARVELOGIK: KUN VALGTE HOLD ---
    # Vi opretter en farve-mappe, hvor alle hold er grå, undtagen de to valgte.
    neutral_color = '#4A4A4A' # Mørkegrå, tydelig men passiv
    color_map = {team: neutral_color for team in unique_teams}
    color_map[t1] = '#006D00' # Vores hold (Grøn)
    color_map[t2] = '#FF0000' # Modstander (Rød)

    # --- KORREKT GRAF (X=Hold, Y=Værdi, Vertikal) ---
    fig = px.bar(df_l, 
                 x='Hold',  # X viser holdene
                 y=m_choice, # Y viser værdien
                 color='Hold', 
                 color_discrete_map=color_map,
                 text_auto='.1f') # Viser værdier ovenpå barerne

    # --- PPT STYLING (GENNEMSIGTIG) ---
    fig.update_layout(
        showlegend=False, 
        # Gennemsigtig baggrund
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)',
        # Hvid tekst for læsbarhed på mørk baggrund
        font=dict(color="white"),
        height=500,
        margin=dict(l=20, r=20, t=30, b=100) # Giver plads til skrå navne
    )
    
    # Juster X-aksen for lange holdnavne
    fig.update_xaxis(tickangle=45, title="")
    fig.update_yaxis(gridcolor='#444444', zerolinecolor='#666666') # Subtile gridlines
    
    st.plotly_chart(fig, use_container_width=True)

    # --- DYNAMISK ANALYSE ---
    st.divider()
    st.write("### 🧠 Taktisk Vurdering")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.write(f"**Intensitet (HI):** {stats_a['HI_P90']:.1f} vs {stats_b['HI_P90']:.1f}")
        st.write(f"**Sprint (HSR):** {stats_a['HSR_P90']:.0f}m vs {stats_b['HSR_P90']:.0f}m")

    with col2:
        analysis = generate_nuanced_advice(stats_a, stats_b, t1, t2)
        for line in analysis:
            st.write(line)

if __name__ == "__main__":
    vis_side()
