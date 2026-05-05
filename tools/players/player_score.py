import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- HJÆLPEFUNKTIONER ---
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

    st.title("🎯 Spilleranalyse | Performance Score")
    st.caption("Sammenligning af spillere baseret på positions-vægtede metrics pr. 90 minutter.")

    conn = _get_snowflake_conn()
    if not conn: return

    # --- 1. KONFIGURATION AF VÆGTNINGER ---
    # Vi bruger rene ASCII-nøgler her, der matcher SQL-outputtet 100%
    POS_CONFIG = {
        "Angriber": {
            "metrics": ["goals", "xg", "shots", "touches_in_box", "dribbles", "assists"],
            "weights": [6.0, 4.0, 3.8, 2.4, 1.2, 2.0],
            "labels": ["Mål", "xG", "Skud", "Felt-berøringer", "Driblinger", "Assists"]
        },
        "Midtbane": {
            "metrics": ["pass_pct", "key_passes", "interceptions", "assists", "tackles", "dribbles"],
            "weights": [8.0, 4.5, 3.0, 4.0, 2.0, 1.5],
            "labels": ["Pasning %", "Key Passes", "Interceptions", "Assists", "Tacklinger", "Driblinger"]
        },
        "Forsvar": {
            "metrics": ["interceptions", "tackles", "clearances", "aerials_won", "pass_pct", "turnovers_def"],
            "weights": [5.0, 4.0, 3.5, 4.0, 2.5, -3.0], 
            "labels": ["Interceptions", "Tacklinger", "Clearinger", "Luftdueller", "Pasning %", "Boldtab"]
        }
    }

    # --- 2. FILTRE ---
    col1, col2, col3 = st.columns(3)
    valgt_pos = col1.selectbox("Vælg Positionsprofil", list(POS_CONFIG.keys()))
    min_mins = col2.slider("Min. minutter spillet", 0, 1500, 270)
    
    # --- 3. DATAFETCH (Snowflake SQL uden specialtegn i aliaser) ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

    with st.spinner("Beregner scores..."):
        sql = f"""
        WITH PlayerStats AS (
            SELECT 
                e.PLAYER_OPTAUUID,
                ANY_VALUE(TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME)) as FULL_NAME,
                ANY_VALUE(m.CONTESTANT_NAME) as TEAM_NAME,
                
                -- Minutes, xG og xA (Omskrevet til Snowflake-sikker syntaks uden FILTER)
                SUM(CASE WHEN mx.STAT_TYPE = 'minsPlayed' THEN mx.STAT_VALUE ELSE 0 END) as total_minutes,
                SUM(CASE WHEN mx.STAT_TYPE = 'expectedGoals' THEN mx.STAT_VALUE ELSE 0 END) as total_xg,
                SUM(CASE WHEN mx.STAT_TYPE = 'expectedAssists' THEN mx.STAT_VALUE ELSE 0 END) as total_xa,
                
                -- Event counts omdøbt til ASCII
                SUM(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 ELSE 0 END) as goals,
                SUM(CASE WHEN e.EVENT_TYPEID IN (13,14,15,16) THEN 1 ELSE 0 END) as shots,
                SUM(CASE WHEN e.EVENT_TYPEID = 1 THEN 1 ELSE 0 END) as passes_attempted,
                SUM(CASE WHEN e.EVENT_TYPEID = 1 AND e.EVENT_OUTCOME = 1 THEN 1 ELSE 0 END) as passes_completed,
                SUM(CASE WHEN e.EVENT_TYPEID = 3 THEN 1 ELSE 0 END) as dribbles,
                
                -- Berøringer i feltet (X over 83, Y mellem 21 og 79)
                SUM(CASE WHEN e.EVENT_X > 83 AND e.EVENT_Y >= 21 AND e.EVENT_Y <= 79 THEN 1 ELSE 0 END) as touches_in_box,
                SUM(CASE WHEN e.EVENT_TYPEID = 8 THEN 1 ELSE 0 END) as interceptions,
                SUM(CASE WHEN e.EVENT_TYPEID = 7 THEN 1 ELSE 0 END) as tackles,
                SUM(CASE WHEN e.EVENT_TYPEID = 12 THEN 1 ELSE 0 END) as clearances,
                
                -- Key Passes (Qualifier 210)
                SUM(CASE WHEN q.QUALIFIER_QID = '210' THEN 1 ELSE 0 END) as key_passes,
                
                -- Luftdueller (Event 44 og vundet)
                SUM(CASE WHEN e.EVENT_TYPEID = 44 AND e.EVENT_OUTCOME = 1 THEN 1 ELSE 0 END) as aerials_won,
                
                -- Boldtab i egen zone (Egen zone defineret som X < 50)
                SUM(CASE WHEN e.EVENT_TYPEID IN (50, 51) AND e.EVENT_X < 50 THEN 1 ELSE 0 END) as turnovers_def
                
            FROM {DB}.OPTA_EVENTS e
            JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            JOIN {DB}.OPTA_MATCHINFO m ON e.EVENT_MATCH_OPTAUUID = m.MATCH_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            LEFT JOIN {DB}.OPTA_MATCHEXPECTEDGOALS mx ON e.PLAYER_OPTAUUID = mx.PLAYER_OPTAUUID AND e.EVENT_MATCH_OPTAUUID = mx.MATCH_ID
            WHERE e.EVENT_TIMESTAMP >= '2025-07-01'
            GROUP BY e.PLAYER_OPTAUUID
        )
        SELECT * FROM PlayerStats WHERE total_minutes >= {min_mins}
        """
        df = conn.query(sql)
        
        if df is not None and not df.empty:
            df.columns = df.columns.str.lower()
            df['visningsnavn'] = df['full_name'].apply(forkort_navn)
            
            # --- 4. P90 BEREGNING OG SCORING ---
            config = POS_CONFIG[valgt_pos]
            
            # Omregn til P90
            df['goals_p90'] = (df['goals'] / df['total_minutes']) * 90
            df['xg_p90'] = (df['total_xg'] / df['total_minutes']) * 90
            df['shots_p90'] = (df['shots'] / df['total_minutes']) * 90
            df['touches_in_box_p90'] = (df['touches_in_box'] / df['total_minutes']) * 90
            df['dribbles_p90'] = (df['dribbles'] / df['total_minutes']) * 90
            df['pass_pct'] = (df['passes_completed'] / df['passes_attempted'].replace(0, 1)) * 100
            df['interceptions_p90'] = (df['interceptions'] / df['total_minutes']) * 90
            df['tackles_p90'] = (df['tackles'] / df['total_minutes']) * 90
            df['clearances_p90'] = (df['clearances'] / df['total_minutes']) * 90
            df['key_passes_p90'] = (df['key_passes'] / df['total_minutes']) * 90
            df['aerials_won_p90'] = (df['aerials_won'] / df['total_minutes']) * 90
            df['turnovers_def_p90'] = (df['turnovers_def'] / df['total_minutes']) * 90
            
            # xA bruges som assist-metrik
            df['assists_p90'] = (df['total_xa'] / df['total_minutes']) * 90

            # BEREGN PERFORMANCE SCORE
            score_col = 'pos_score'
            df[score_col] = 0.0
            
            for i, m_name in enumerate(config['metrics']):
                col_name = f"{m_name}_p90" if m_name != "pass_pct" else m_name
                weight = config['weights'][i]
                df[score_col] += df[col_name] * weight

            # Rund scoren til 1 decimal
            df[score_col] = df[score_col].round(1)
            
            # --- 5. VISNING ---
            top_10 = df.sort_values(score_col, ascending=False).head(10)

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
                    top_10[['visningsnavn', 'team_name', score_col, 'total_minutes']],
                    column_config={
                        "visningsnavn": "Spiller",
                        "team_name": "Hold",
                        "pos_score": "Score",
                        "total_minutes": "Min"
                    },
                    hide_index=True,
                    use_container_width=True
                )

            # --- 6. FORMEL FORKLARING ---
            with st.expander("Se beregnings-metode"):
                st.write(f"**Formel for {valgt_pos}:**")
                formula_text = " + ".join([f"({config['labels'][i]} * {config['weights'][i]})" for i in range(len(config['metrics']))])
                st.code(f"Score = {formula_text}")
                st.caption("Alle volumetal er normaliseret til pr. 90 minutter.")

        else:
            st.info("Ingen spillere fundet med de valgte kriterier.")

if __name__ == "__main__":
    vis_side()
