import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- HJÆLPEFUNKTIONER (Genbrug fra din profil-side) ---
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
    # Her kan du justere tallene præcis som du ønsker
    POS_CONFIG = {
        "Angriber": {
            "metrics": ["mål", "xg", "afslutninger", "berøringer_i_felt", "driblinger", "assists"],
            "weights": [6.0, 4.0, 3.8, 2.4, 1.2, 2.0],
            "labels": ["Mål", "xG", "Skud", "Felt-berøringer", "Driblinger", "Assists"]
        },
        "Midtbane": {
            "metrics": ["pasning_pct", "key_passes", "interceptions", "assists", "vundne_dueller", "progressive_runs"],
            "weights": [8.0, 4.5, 3.0, 4.0, 2.0, 1.5],
            "labels": ["Pasning %", "Key Passes", "Interceptions", "Assists", "Vundne Dueller", "Prog. Løb"]
        },
        "Forsvar": {
            "metrics": ["interceptions", "tacklinger", "clearances", "luftdueller_vundet", "pasning_pct", "boldtab_forsvar"],
            "weights": [5.0, 4.0, 3.5, 4.0, 2.5, -3.0], # Boldtab i forsvaret trækker ned
            "labels": ["Interceptions", "Tacklinger", "Clearinger", "Luftdueller", "Pasning %", "Boldtab"]
        }
    }

    # --- 2. FILTRE ---
    col1, col2, col3 = st.columns(3)
    valgt_pos = col1.selectbox("Vælg Positionsprofil", list(POS_CONFIG.keys()))
    min_mins = col2.slider("Min. minutter spillet", 0, 1500, 270)
    
    # --- 3. DATAFETCH (Optimeret SQL) ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_IDS = "('335', '328', '329', '43319', '331')" # Kan udvides

    with st.spinner("Beregner scores..."):
        sql = f"""
        WITH PlayerStats AS (
            SELECT 
                e.PLAYER_OPTAUUID,
                ANY_VALUE(TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME)) as FULL_NAME,
                ANY_VALUE(m.CONTESTANT_NAME) as TEAM_NAME,
                -- Minutes, xG, xA fra expected tabellen
                SUM(mx.STAT_VALUE) FILTER (WHERE mx.STAT_TYPE = 'minsPlayed') as total_minutes,
                SUM(mx.STAT_VALUE) FILTER (WHERE mx.STAT_TYPE = 'expectedGoals') as total_xg,
                -- Event counts
                COUNT(e.EVENT_OPTAUUID) FILTER (WHERE e.EVENT_TYPEID = 16) as mål,
                COUNT(e.EVENT_OPTAUUID) FILTER (WHERE e.EVENT_TYPEID IN (13,14,15,16)) as afslutninger,
                COUNT(e.EVENT_OPTAUUID) FILTER (WHERE e.EVENT_TYPEID = 1) as pasninger_forsøg,
                COUNT(e.EVENT_OPTAUUID) FILTER (WHERE e.EVENT_TYPEID = 1 AND e.EVENT_OUTCOME = 1) as pasninger_succes,
                COUNT(e.EVENT_OPTAUUID) FILTER (WHERE e.EVENT_TYPEID = 3) as driblinger,
                -- Område-bestemt: Berøringer i feltet (Opta koordinater > 83)
                COUNT(e.EVENT_OPTAUUID) FILTER (WHERE e.EVENT_X > 83 AND e.EVENT_Y BETWEEN 21 AND 79) as berøringer_i_felt,
                COUNT(e.EVENT_OPTAUUID) FILTER (WHERE e.EVENT_TYPEID = 8) as interceptions,
                COUNT(e.EVENT_OPTAUUID) FILTER (WHERE e.EVENT_TYPEID = 7) as tacklinger
            FROM {DB}.OPTA_EVENTS e
            JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            JOIN {DB}.OPTA_MATCHINFO m ON e.EVENT_MATCH_OPTAUUID = m.MATCH_OPTAUUID
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
            
            # Beregn grund-metrics (håndter division med nul)
            df['mål_p90'] = (df['mål'] / df['total_minutes']) * 90
            df['xg_p90'] = (df['total_xg'] / df['total_minutes']) * 90
            df['afslutninger_p90'] = (df['afslutninger'] / df['total_minutes']) * 90
            df['berøringer_i_felt_p90'] = (df['berøringer_i_felt'] / df['total_minutes']) * 90
            df['driblinger_p90'] = (df['driblinger'] / df['total_minutes']) * 90
            df['pasning_pct'] = (df['pasninger_succes'] / df['pasninger_forsøg'].replace(0, 1)) * 100
            df['interceptions_p90'] = (df['interceptions'] / df['total_minutes']) * 90
            df['tacklinger_p90'] = (df['tacklinger'] / df['total_minutes']) * 90
            
            # Dummy værdier for dem vi mangler i dette SQL eksempel (assists etc kan tilføjes i SQL'en)
            df['assists_p90'] = 0.15 
            df['key_passes_p90'] = 1.2
            df['vundne_dueller_p90'] = 4.5
            df['progressive_runs_p90'] = 2.1
            df['clearances_p90'] = 3.0
            df['luftdueller_vundet_p90'] = 2.0
            df['boldtab_forsvar_p90'] = 0.5

            # BEREGN PERFORMANCE SCORE (Din formel)
            # Vi mapper de valgte metrics til deres P90 navne
            score_col = 'pos_score'
            df[score_col] = 0
            
            for i, m_name in enumerate(config['metrics']):
                # Find kolonnenavnet (enten _p90 eller rå som pasning_pct)
                col_name = f"{m_name}_p90" if m_name != "pasning_pct" else m_name
                weight = config['weights'][i]
                df[score_col] += df[col_name] * weight

            # Rund scoren
            df[score_col] = df[score_col].round(1)
            
            # --- 5. VISNING ---
            top_10 = df.sort_values(score_col, ascending=False).head(10)

            col_main, col_stats = st.columns([2, 1])

            with col_main:
                st.subheader(f"Top 10: {valgt_pos}")
                
                # Plotly Bar Chart
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
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=500)
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
                st.caption("Alle volumetal (mål, skud osv.) er normaliseret til pr. 90 minutter.")

        else:
            st.info("Ingen spillere fundet med de valgte kriterier.")

if __name__ == "__main__":
    vis_side()
