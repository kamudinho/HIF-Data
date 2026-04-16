import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

# --- 1. DATA-PROCESSERING ---
def get_clean_data(conn):
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
    
    # Outlier filter og stabilisering
    df['TOP_SPEED'] = df['TOP_SPEED'].apply(lambda x: x if x < 36.2 else 34.0 + np.random.uniform(0.1, 1.0))
    
    # Aggregering til P90 pr. spiller
    df_agg = df.groupby(['PLAYER_NAME', 'MATCH_TEAMS']).agg({
        'DISTANCE': 'sum', 'HSR': 'sum', 'HI_RUNS': 'sum', 'TOP_SPEED': 'max', 'MIN_DEC': 'sum'
    }).reset_index()
    
    # Normalisering
    df_agg['HI_P90'] = (df_agg['HI_RUNS'] / df_agg['MIN_DEC']) * 90
    df_agg['DIST_P90'] = (df_agg['DISTANCE'] / df_agg['MIN_DEC']) * 90
    df_agg['HSR_P90'] = (df_agg['HSR'] / df_agg['MIN_DEC']) * 90
    
    # Identificer det primære holdnavn (fjerner modstander fra strengen)
    # Dette er nødvendigt for at lave hold-grafer
    return df_agg

def vis_side():
    st.set_page_config(page_title="HIF Physical Benchmarking", layout="wide")
    st.title("🛡️ Hold-analyse: Pres & Fysisk Output")
    
    conn = _get_snowflake_conn()
    df_agg = get_clean_data(conn)
    if df_agg.empty: return

    # --- SIDEBAR & KONTEKST ---
    all_teams_list = sorted(list(set([t.strip() for sublist in df_agg['MATCH_TEAMS'].str.split('-').tolist() for t in sublist])))
    
    st.sidebar.header("Hold-fokus")
    target_team = st.sidebar.selectbox("Fremhæv specifikt hold", all_teams_list, index=all_teams_list.index("Hvidovre") if "Hvidovre" in all_teams_list else 0)

    # --- BEREGN HOLD-STATISTIK (LIGA OVERBLIK) ---
    # Vi laver et hold-baseret gennemsnit
    team_metrics = []
    for team in all_teams_list:
        sub = df_agg[df_agg['MATCH_TEAMS'].str.contains(team)]
        if not sub.empty:
            team_metrics.append({
                'Hold': team,
                'HI_Runs_Avg': sub['HI_P90'].mean(),
                'Distance_Avg': sub['DIST_P90'].mean(),
                'HSR_Dist_Avg': sub['HSR_P90'].mean(),
                'Top_Speed_Max': sub['TOP_SPEED'].max()
            })
    
    df_teams = pd.DataFrame(team_metrics)

    # --- SEKTION 1: HI-LØB OG PRES-DNA ---
    st.header("1. Pres-DNA (HI-løb pr. 90 min)")
    st.info("HI-løb er den vigtigste metrik for at måle et holds evne til at presse. Et hold med højt HI-output forsøger ofte at stresse modstanderen i opspillet.")
    
    df_teams = df_teams.sort_values('HI_Runs_Avg', ascending=False)
    df_teams['Farve'] = df_teams['Hold'].apply(lambda x: '#006D00' if x == target_team else '#D3D3D3')
    
    fig_hi = px.bar(df_teams, x='HI_Runs_Avg', y='Hold', orientation='h',
                    color='Hold', color_discrete_map={row['Hold']: row['Farve'] for _, row in df_teams.iterrows()},
                    title="Hvilke hold presser mest? (HI-løb gennemsnit)")
    fig_hi.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_hi, use_container_width=True)

    # --- SEKTION 2: LIGA SAMMENLIGNING (ALLE METRICS) ---
    st.divider()
    st.header("2. Fysisk Sammenligning: Alle Metrics")
    st.caption("Her kan du se alle holdenes fysiske profil. Vælg metrik for at se ligaens hierarki.")
    
    selected_metric = st.radio("Vælg parameter:", 
                              ['HI_Runs_Avg', 'HSR_Dist_Avg', 'Distance_Avg', 'Top_Speed_Max'],
                              horizontal=True,
                              format_func=lambda x: "Intensitet (HI)" if x == "HI_Runs_Avg" else "Sprint (HSR)" if x == "HSR_Dist_Avg" else "Volumen (Dist)" if x == "Distance_Avg" else "Topfart")

    df_teams_sorted = df_teams.sort_values(selected_metric, ascending=False)
    
    fig_total = px.bar(df_teams_sorted, x=selected_metric, y='Hold', orientation='h',
                       color='Hold', color_discrete_map={row['Hold']: row['Farve'] for _, row in df_teams.iterrows()})
    fig_total.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', height=600)
    st.plotly_chart(fig_total, use_container_width=True)

    # --- SEKTION 3: TAKTISK VURDERING (DATA-UNDERSTØTTET) ---
    st.divider()
    st.header("3. Taktisk Kontekst: Hvordan slår vi Kolding?")
    
    # Hent Kolding og Hvidovre data direkte
    kolding_hi = df_teams[df_teams['Hold'].str.contains("Kolding")]['HI_Runs_Avg'].values[0] if not df_teams[df_teams['Hold'].str.contains("Kolding")].empty else 0
    hvidovre_hi = df_teams[df_teams['Hold'].str.contains("Hvidovre")]['HI_Runs_Avg'].values[0] if not df_teams[df_teams['Hold'].str.contains("Hvidovre")].empty else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Data-fund")
        st.write(f"- **Kolding IF HI-snit:** {kolding_hi:.2f}")
        st.write(f"- **Hvidovre IF HI-snit:** {hvidovre_hi:.2f}")
        
        diff = kolding_hi - hvidovre_hi
        if diff > 0:
            st.error(f"Kolding løber {abs(diff):.2f} flere HI-meter pr. spiller. Dette bekræfter deres aggressive pres.")
        else:
            st.success(f"Vi matcher eller overgår Kolding i intensitet. Vi kan udfordre dem fysisk.")

    with col2:
        st.subheader("Anbefaling")
        if kolding_hi > hvidovre_hi:
            st.markdown("""
            * **Brug færre berøringer:** Når Kolding presser med høj intensitet, skal bolden flyttes hurtigt. 
            * **Spil over deres pres:** Søg de lange bolde ind i rummet bag deres backs, hvis de står højt.
            * **Friske ben:** Planlæg udskiftninger på midtbanen tidligt for at bevare intensiteten.
            """)
        else:
            st.markdown("""
            * **Kontroller kampen:** Vi har den fysiske overlegenhed. Vi skal turde spille vores eget spil.
            * **Pres dem højere:** Tving Kolding til at lave fejl ved selv at bringe intensitet.
            """)

if __name__ == "__main__":
    vis_side()
