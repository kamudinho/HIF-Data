import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn

# --- Konfiguration ---
st.set_page_config(page_title="Hvidovre IF Dynamisk Modstander-Analyse", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #1E1E1E; color: white; }
    .stSelectbox div[data-baseweb="select"] > div { background-color: #2D2D2D; color: white; }
    hr { border-color: #444444; }
</style>
""", unsafe_allow_html=True)

# --- 1. DATA-PROCESSERING ---
def get_league_data(conn):
    sql = """
        SELECT 
            P.MATCH_TEAMS, P.DISTANCE, 
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
    
    # Aggregering til hold-niveau
    df['HI_P90'] = (df['HI_RUNS'] / df['MIN_DEC']) * 90
    df['HSR_P90'] = (df['HSR'] / df['MIN_DEC']) * 90
    df['DIST_P90'] = (df['DISTANCE'] / df['MIN_DEC']) * 90
    
    return df

# --- 2. DEN DYNAMISKE ANALYSE-MOTOR (Ingen hardcoding) ---
def analyze_opponent_dna(target_stats, league_avg):
    dna = {"stil": "", "mønster": "", "modtræk": []}
    
    # Vurdering af Pres-intensitet
    hi_ratio = target_stats['HI_P90'] / league_avg['HI_P90']
    if hi_ratio > 1.10:
        dna["stil"] = "Ekstremt aggressivt pres-hold"
        dna["mønster"] = "Søger konsekvent 1-mod-1 dueller og forsøger at fremprovokere fejl i jeres opspil."
        dna["modtræk"].append("Brug færre berøringer centralt - bolden skal flyttes hurtigere end deres pres.")
        dna["modtræk"].append("Søg de direkte bolde i bagrummet tidligt, da de står meget højt.")
    elif hi_ratio < 0.90:
        dna["stil"] = "Passivt / Kompakt defensiv"
        dna["mønster"] = "Falder dybt og lader jer have bolden. Satser på at lukke rummene centralt."
        dna["modtræk"].append("Tålmodighed i opbygningen - flyt dem fra side til side for at åbne mellemrum.")
        dna["modtræk"].append("Gå efter indlæg eller langskud, når de pakker sig i feltet.")
    else:
        dna["stil"] = "Balanceret organisation"
        dna["mønster"] = "Varierer deres pres alt efter kampens fase."
        dna["modtræk"].append("Fokusér på restforsvar og vind de løse bolde på midten.")

    # Vurdering af Omstillings-farlighed (HSR)
    hsr_ratio = target_stats['HSR_P90'] / league_avg['HSR_P90']
    if hsr_ratio > 1.15:
        dna["mønster"] += " Ekstremt farlige i vertikale omstillinger."
        dna["modtræk"].append("Prioritér et stærkt restforsvar (3+2 struktur) for at dæmme op for deres kontraløb.")

    return dna

# --- 3. UI OG VISNING ---
def vis_side():
    st.title("Dynamisk Taktisk Modstander-Analyse")
    
    conn = _get_snowflake_conn()
    df = get_league_data(conn)
    if df.empty: return

    unique_teams = sorted(list(set([t.strip() for sublist in df['MATCH_TEAMS'].str.split('-').tolist() for t in sublist])))
    
    col_a, col_b = st.columns(2)
    with col_a:
        t1 = st.selectbox("Vores Hold", unique_teams, index=unique_teams.index("Hvidovre") if "Hvidovre" in unique_teams else 0)
    with col_b:
        t2 = st.selectbox("Modstander", unique_teams, index=unique_teams.index("Kolding IF") if "Kolding IF" in unique_teams else 0)

    # Beregn stats
    def get_team_avg(name):
        mask = df['MATCH_TEAMS'].str.contains(name)
        return df[mask][['HI_P90', 'HSR_P90', 'TOP_SPEED', 'DIST_P90']].mean()

    stats_hvi = get_team_avg(t1)
    stats_opp = get_team_avg(t2)
    league_avg = df[['HI_P90', 'HSR_P90', 'TOP_SPEED', 'DIST_P90']].mean()

    # Analyse
    dna = analyze_opponent_dna(stats_opp, league_avg)

    # Graf
    st.divider()
    metrics = pd.DataFrame({
        'Parameter': ['HI Løb', 'Sprint (HSR)', 'Total Distance'],
        t1: [stats_hvi['HI_P90'], stats_hvi['HSR_P90'], stats_hvi['DIST_P90']],
        t2: [stats_opp['HI_P90'], stats_opp['HSR_P90'], stats_opp['DIST_P90']],
        'Liga Snit': [league_avg['HI_P90'], league_avg['HSR_P90'], league_avg['DIST_P90']]
    })
    
    fig = px.bar(metrics, x='Parameter', y=[t1, t2, 'Liga Snit'], barmode='group',
                 color_discrete_map={t1: '#006D00', t2: '#FF0000', 'Liga Snit': '#4A4A4A'})
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), barmode='group')
    st.plotly_chart(fig, use_container_width=True)

    # Dynamisk Tekst-felt
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"Profil af {t2}")
        st.write(f"**Stil:** {dna['stil']}")
        st.write(f"**Mønster:** {dna['mønster']}")
    
    with c2:
        st.subheader("Plan: Hvordan vi slår dem")
        for m in dna["modtræk"]:
            st.write(f"- {m}")

if __name__ == "__main__":
    vis_side()
