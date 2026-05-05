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

    DB = "KLUB_HVIDOVREIF.AXIS"

    # --- 1. DYNAMISKE FILTRE (Hent direkte fra DB) ---
    try:
        # Hent unikke liga-ID'er der faktisk har data i din tabel
        liga_data = conn.query(f"SELECT DISTINCT COMPETITION_WYID FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE")
        ligaer = sorted([int(x) for x in liga_data['COMPETITION_WYID'].dropna().tolist()]) if liga_data is not None else [328, 1305]
        
        # Hent unikke sæson-ID'er der faktisk har data i din tabel
        saeson_data = conn.query(f"SELECT DISTINCT SEASON_WYID FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE")
        saesoner = sorted([int(x) for x in saeson_data['SEASON_WYID'].dropna().tolist()], reverse=True) if saeson_data is not None else [189030]
    except Exception as e:
        st.warning(f"Kunne ikke hente dynamiske filtre (bruger standardværdier): {e}")
        ligaer = [328, 1305]
        saesoner = [189030]

    # Navne-mapping til de mest gængse ligaer i dit system
    LIGA_MAP = {
        328: "NordicBet Liga (328)",
        335: "Superliga (335)",
        329: "2. division (329)",
        43319: "3. division (43319)",
        331: "Oddset Pokalen (331)",
        1305: "U19 Ligaen (1305)"
    }

    col1, col2, col3 = st.columns(3)
    
    # 1. Vælg positionsprofil
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
    valgt_pos = col1.selectbox("Vælg Positionsprofil", list(POS_CONFIG.keys()))
    
    # 2. Vælg liga (Dynamisk)
    valgt_liga = col2.selectbox(
        "Vælg Liga", 
        ligaer, 
        format_func=lambda x: LIGA_MAP.get(x, f"Liga ID: {x}")
    )
    
    # 3. Vælg Sæson (Dynamisk)
    valgt_saeson = col3.selectbox(
        "Vælg Sæson ID", 
        saesoner,
        format_func=lambda x: f"Sæson: {x} (2025/2026)" if x == 189030 else f"Sæson ID: {x}"
    )

    # --- 2. DATAFETCH ---
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
            s.ARIALDUELS AS AERIALDUELS, -- Rettet stavning
            s.DANGEROUSOWNHALFLOSSES,
            s.ASSISTS
        FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE s
        JOIN {DB}.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
        JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
        WHERE s.COMPETITION_WYID = {valgt_liga}
          AND s.SEASON_WYID = {valgt_saeson}
        """
        
        df = conn.query(sql)
        
        if df is not None and not df.empty:
            df.columns = df.columns.str.lower()
            df['visningsnavn'] = df['full_name'].apply(forkort_navn)
            
            # --- 3. BEREGNING AF PASNINGSPROCENT ---
            df['pass_pct'] = (df['successfulpasses'] / df['passes'].replace(0, 1)) * 100

            # Find den valgte profilkonfiguration
            config = POS_CONFIG[valgt_pos]
            
            # BEREGN DIN POS-SCORE
            score_col = 'pos_score'
            df[score_col] = 0.0
            
            for i, m_name in enumerate(config['metrics']):
                weight = config['weights'][i]
                df[score_col] += df[m_name] * weight

            df[score_col] = df[score_col].round(1)
            
            # Sorter efter højeste score
            top_10 = df.sort_values(score_col, ascending=False).head(10)

            # --- 4. VISNING ---
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

            # --- 5. METODEFORKLARING ---
            with st.expander("Se beregnings-metode"):
                st.write(f"**Formel for {valgt_pos}:**")
                formula_text = " + ".join([f"({config['labels'][i]} * {config['weights'][i]})" for i in range(len(config['metrics']))])
                st.code(f"Score = {formula_text}")
                st.caption("Data leveres direkte som gennemsnit pr. 90 minutter (P90) fra Wyscout API'et.")

        else:
            st.info("Ingen spillere fundet i systemet med de angivne kriterier. Prøv at skifte liga eller sæson i dropdown-menuerne.")

if __name__ == "__main__":
    vis_side()
