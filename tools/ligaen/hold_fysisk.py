import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.markdown("""<style>
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #333; }
    </style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # SQL: Aggregering pr. hold baseret på dine kolonner
    # Vi tager gennemsnittet af alle rækker for hver unikt MATCH_TEAMS
    sql_liga = f"""
        SELECT 
            MATCH_TEAMS,
            AVG(DISTANCE) as AVG_DIST,
            AVG("HIGH SPEED RUNNING") as AVG_HSR,
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as AVG_HI,
            AVG(TOP_SPEED) as AVG_PEAK_SPEED
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE >= '{SEASON_START}'
        GROUP BY MATCH_TEAMS
    """
    
    df_liga = conn.query(sql_liga)

    if df_liga is None or df_liga.empty:
        st.error("Kunne ikke hente data.")
        return

    # SIKRING: Tving store bogstaver og rens navne
    df_liga.columns = [c.upper() for c in df_liga.columns]
    
    # RENSNING: Da MATCH_TEAMS i dine data ofte er "HOLD-MODSTANDER", 
    # splitter vi det så vi får det primære holdnavn
    df_liga['TEAM_CLEAN'] = df_liga['MATCH_TEAMS'].apply(lambda x: str(x).split('-')[0].strip())
    
    # Nu grupperer vi igen i Pandas for at samle alle "B93-..." rækker til én "B93" række
    df_final = df_liga.groupby('TEAM_CLEAN').agg({
        'AVG_DIST': 'mean',
        'AVG_HSR': 'mean',
        'AVG_HI': 'mean',
        'AVG_PEAK_SPEED': 'mean'
    }).reset_index()

    # 1. VALG AF HOLD
    valgt_hold = st.selectbox("Vælg Hold", sorted(df_final['TEAM_CLEAN'].unique()))
    
    hold_stats = df_final[df_final['TEAM_CLEAN'] == valgt_hold].iloc[0]
    liga_snit = df_final.mean(numeric_only=True)

    # 2. TOP METRIKKER (Sæson-gennemsnit)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gns. Distance", f"{round(hold_stats['AVG_DIST']/1000, 1)} km")
    m2.metric("Gns. HSR", f"{int(hold_stats['AVG_HSR'])} m")
    m3.metric("Gns. HI løb", f"{int(hold_stats['AVG_HI'])}")
    m4.metric("Gns. Topfart", f"{round(hold_stats['AVG_PEAK_SPEED'], 1)} km/t")

    st.divider()

    # 3. SCATTER PLOT (Nu med kun én prik pr. hold)
    st.subheader("Holdets placering i ligaen (Sæson-gennemsnit)")
    
    fig = px.scatter(
        df_final, 
        x='AVG_HI', 
        y='AVG_PEAK_SPEED',
        text='TEAM_CLEAN',
        labels={
            'AVG_HI': 'High Intensity Aktiviteter (Gns. pr. kamp)',
            'AVG_PEAK_SPEED': 'Topfart (Gns. pr. kamp - km/t)'
        }
    )

    fig.update_traces(
        marker=dict(size=14, opacity=0.4, color='grey'),
        textposition='top center'
    )

    # Fremhæv det valgte hold
    highlight = df_final[df_final['TEAM_CLEAN'] == valgt_hold]
    fig.add_trace(go.Scatter(
        x=highlight['AVG_HI'],
        y=highlight['AVG_PEAK_SPEED'],
        mode='markers+text',
        marker=dict(size=22, color='#cc0000', line=dict(width=2, color='white')),
        text=[valgt_hold],
        textposition="top center",
        showlegend=False
    ))

    # Gennemsnitslinjer
    fig.add_vline(x=liga_snit['AVG_HI'], line_dash="dash", line_color="grey", opacity=0.5)
    fig.add_hline(y=liga_snit['AVG_PEAK_SPEED'], line_dash="dash", line_color="grey", opacity=0.5)

    fig.update_layout(
        height=600, 
        template="plotly_white",
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
