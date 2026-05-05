import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn

def forkort_navn(navn_str):
    if not navn_str or not isinstance(navn_str, str): return ""
    dele = [d.strip() for d in navn_str.split() if d.strip()]
    if len(dele) <= 2: return " ".join(dele)
    return f"{dele[0]} {dele[-1]}"

def vis_side():
    st.markdown("""
        <style>
        .score-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #df003b; margin-bottom: 20px; }
        .pos-title { font-size: 24px; font-weight: bold; color: #1E1E1E; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🎯 Spilleranalyse | Performance Score (Wyscout)")
    st.caption("Sammenligning af spillere baseret på positions-vægtede Wyscout P90-metrics.")

    conn = _get_snowflake_conn()
    if not conn: return

    # --- 1. KONFIGURATION AF VÆGTNINGER ---
    POS_CONFIG = {
        "Angriber": {
            "metrics": ["goals", "xg", "shots", "touchinbox", "dribbles", "assists"],
            "weights": [6.0, 4.0, 3.8, 2.4, 1.2, 2.0],
            "labels": ["Mål", "xG", "Skud", "Berøringer i felt", "Driblinger", "Assists"]
        },
        "Midtbane": {
            "metrics": ["pass_pct", "keypasses", "interceptions", "xgassist", "slidingtackles", "progressiverun"],
            "weights": [8.0, 4.5, 3.0, 4.0, 2.0, 1.5],
            "labels": ["Pasnings %", "Key Passes", "Interceptions", "xA", "Glidende Tacklinger", "Progressive løb"]
        },
        "Forsvar": {
            "metrics": ["interceptions", "defensiveduelswon", "clearances", "aerialduelswon", "pass_pct", "dangerousownhalflosses"],
            "weights": [5.0, 4.0, 3.5, 4.0, 2.5, -3.0], 
            "labels": ["Interceptions", "Vundne Def. Dueller", "Clearinger", "Vundne Luftdueller", "Pasnings %", "Farlige Boldtab (Egen banehalvdel)"]
        }
    }

    # --- 2. FILTRE ---
    col1, col2 = st.columns(2)
    valgt_pos = col1.selectbox("Vælg Positionsprofil", list(POS_CONFIG.keys()))
    
    # Wyscout fastlagte værdier fra dine indstillinger
    SEASON_WYID = 189030 # Svarer til 2025/2026 i din udtrukne data
    COMPETITION_WYID = 328 # NordicBet Liga (eller 1305 for U19 jf. dit seneste udtræk)

    # Mulighed for at skifte liga for test (f.eks. hvis du vil se U19 data i din test)
    valgt_liga = col2.selectbox("Vælg Liga", [328, 1305], format_func=lambda x: "Betinia Ligaen" if x == 328 else "U19 Ligaen")

    # --- 3. DATAFETCH (Optimeret til din præcise Wyscout struktur) ---
    DB = "KLUB_HVIDOVREIF.AXIS"

    with st.spinner("Henter og beregner Wyscout-data..."):
        sql = f"""
        SELECT 
            p.PLAYER_WYID,
            p.SHORTNAME as FULL_NAME,
            t.OFFICIALNAME as TEAM_NAME,
            s.GOALS,
            s.XGSHOT AS XG,
            s.SHOTS,
            s.TOUCHINBOX,
            s.DRIBBLES,
            s.PASSES,
            s.SUCCESSFULPASSES,
            s.KEYPASSES,
            s.INTERCEPTIONS,
            s.XGASSIST,
            s.SLIDINGTACKLES,
            s.PROGRESSIVERUN,
            s.DEFENSIVEDUELSWON,
            s.CLEARANCES,
            s.AERIALDUELS,
            s.DANGEROUSOWNHALFLOSSES,
            s.ASSISTS
        FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE s
        JOIN {DB}.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
        JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
        WHERE s.COMPETITION_WYID = {valgt_liga}
          AND s.SEASON_WYID = {SEASON_WYID}
        """
        
        df = conn.query(sql)
        
        if df is not None and not df.empty:
            df.columns = df.columns.str.lower()
            df['visningsnavn'] = df['full_name'].apply(forkort_navn)
            
            # --- 4. BEREGNING AF PASNINGSPROCENT ---
            # Vi sikrer os mod division med 0 ved at bruge replace(0, 1) på nævneren
            df['pass_pct'] = (df['successfulpasses'] / df['passes'].replace(0, 1)) * 100

            # Find den valgte profilkonfiguration
            config = POS_CONFIG[valgt_pos]
            
            # BEREGN DIN POS-SCORE
            score_col = 'pos_score'
            df[score_col] = 0.0
            
            for i, m_name in enumerate(config['metrics']):
                weight = config['weights'][i]
                df[score_col] += df[m_name] * weight

            # Rund scoren til 1 decimal
            df[score_col] = df[score_col].round(1)
            
            # Sorter efter højeste score
            top_10 = df.sort_values(score_col, ascending=False).head(10)

            # --- 5. VISNING ---
            col_main, col_stats = st.columns([2, 1])

            with col_main:
                st.subheader(f"Top 10: {valgt_pos}")
                
                fig = px.bar(
                    top_10, 
                    x=score_col, 
                    y='visningsnavn', 
                    orientation='h',
                    text=score_col,
                    color=score_col,
                    color_continuous_scale='Reds',
                    labels={'visningsnavn': 'Spiller', 'pos_score': 'Performance Score'},
                    template='plotly_white'
                )
                fig.update_layout(
                    yaxis={'categoryorder':'total ascending'}, 
                    showlegend=False, 
                    height=500,
                    margin=dict(l=5, r=5, t=10, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_stats:
                st.subheader("Data Tabel")
                st.dataframe(
                    top_10[['visningsnavn', 'team_name', score_col]],
                    column_config={
                        "visningsnavn": "Spiller",
                        "team_name": "Hold",
                        "pos_score": "Score"
                    },
                    hide_index=True,
                    use_container_width=True
                )

            # --- 6. METODEFORKLARING ---
            with st.expander("Se beregnings-metode"):
                st.write(f"**Formel for {valgt_pos}:**")
                formula_text = " + ".join([f"({config['labels'][i]} * {config['weights'][i]})" for i in range(len(config['metrics']))])
                st.code(f"Score = {formula_text}")
                st.caption("Data leveres direkte som gennemsnit pr. 90 minutter (P90) fra Wyscout API'et.")

        else:
            st.info("Ingen spillere fundet i systemet med de angivne kriterier.")

if __name__ == "__main__":
    vis_side()
