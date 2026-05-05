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
        .stat-box { background-color: #ffffff; padding: 10px; border: 1px solid #e0e0e0; border-radius: 5px; text-align: center; }
        .stat-val { font-size: 20px; font-weight: bold; color: #df003b; }
        .stat-lbl { font-size: 12px; color: #666; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🎯 Spilleranalyse | Performance Score (Wyscout)")
    st.caption("Sammenligning af spillere baseret på positions-vægtede Wyscout P90-metrics for sæsonen 2025/2026.")

    conn = _get_snowflake_conn()
    if not conn: return

    DB = "KLUB_HVIDOVREIF.AXIS"
    SOGT_SAESON = "2025/2026"

    # --- 1. HENT LIGAER DYNAMISK ---
    try:
        liga_data = conn.query(f"""
            SELECT DISTINCT s.COMPETITION_WYID 
            FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE s
            JOIN {DB}.WYSCOUT_SEASONS seas ON s.SEASON_WYID = seas.SEASON_WYID
            WHERE seas.SEASONNAME = '{SOGT_SAESON}'
        """)
        ligaer = sorted([int(x) for x in liga_data['COMPETITION_WYID'].dropna().tolist()]) if liga_data is not None and not liga_data.empty else [328, 1305]
    except Exception as e:
        st.warning(f"Kunne ikke hente dynamiske ligaer (bruger standard): {e}")
        ligaer = [328, 1305]

    LIGA_MAP = {
        328: "NordicBet Liga (328)",
        335: "Superliga (335)",
        329: "2. division (329)",
        43319: "3. division (43319)",
        331: "Oddset Pokalen (331)",
        1305: "U19 Ligaen (1305)"
    }

    # --- 2. BRUGERGRÆNSEFLADE (Filtre) ---
    col1, col2 = st.columns(2)
    
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
    
    valgt_liga = col2.selectbox(
        "Vælg Liga", 
        ligaer, 
        format_func=lambda x: LIGA_MAP.get(x, f"Liga ID: {x}")
    )

    # --- 3. DATAFETCH ---
    with st.spinner("Henter og beregner Wyscout-data..."):
        sql = f"""
        SELECT 
            p.PLAYER_WYID,
            p.SHORTNAME as FULL_NAME,
            t.OFFICIALNAME as TEAM_NAME,
            AVG(s.GOALS) as GOALS,
            AVG(s.XGSHOT) AS XG,
            AVG(s.SHOTS) as SHOTS,
            AVG(s.TOUCHINBOX) as TOUCHINBOX,
            AVG(s.DRIBBLES) as DRIBBLES,
            AVG(s.PASSES) as PASSES,
            AVG(s.SUCCESSFULPASSES) as SUCCESSFULPASSES,
            AVG(s.KEYPASSES) as KEYPASSES,
            AVG(s.INTERCEPTIONS) as INTERCEPTIONS,
            AVG(s.XGASSIST) as XGASSIST,
            AVG(s.SLIDINGTACKLES) as SLIDINGTACKLES,
            AVG(s.PROGRESSIVERUN) as PROGRESSIVERUN,
            AVG(s.DEFENSIVEDUELSWON) as DEFENSIVEDUELSWON,
            AVG(s.CLEARANCES) as CLEARANCES,
            AVG(s.AERIALDUELS) AS AERIALDUELS,
            AVG(s.DANGEROUSOWNHALFLOSSES) as DANGEROUSOWNHALFLOSSES,
            AVG(s.ASSISTS) as ASSISTS
        FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE s
        JOIN {DB}.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
        JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
        JOIN {DB}.WYSCOUT_SEASONS seas ON s.SEASON_WYID = seas.SEASON_WYID
        WHERE s.COMPETITION_WYID = {valgt_liga}
          AND seas.SEASONNAME = '{SOGT_SAESON}'
        GROUP BY p.PLAYER_WYID, p.SHORTNAME, t.OFFICIALNAME, p.CURRENTTEAM_WYID
        """
        
        df = conn.query(sql)
        
        if df is not None and not df.empty:
            df.columns = df.columns.str.lower()
            df['visningsnavn'] = df['full_name'].apply(forkort_navn)
            
            # --- 4. BEREGNING AF PASNINGSPROCENT ---
            df['pass_pct'] = (df['successfulpasses'] / df['passes'].replace(0, 1)) * 100

            # Find den valgte profilkonfiguration
            config = POS_CONFIG[valgt_pos]
            
            # BEREGN PERFORMANCE SCORE
            score_col = 'pos_score'
            df[score_col] = 0.0
            
            for i, m_name in enumerate(config['metrics']):
                weight = config['weights'][i]
                df[score_col] += df[m_name] * weight

            df[score_col] = df[score_col].round(1)
            
            # Sortér alle spillere efter højeste score til barchart
            df_alle = df.sort_values(score_col, ascending=True)

            # Dynamisk højde på grafen baseret på antal spillere
            hoejde_graf = max(400, len(df_alle) * 20)

            # --- 5. VISNING AF ALLE SPILLERE (BARCHART) ---
            st.subheader(f"Performance Score for alle spillere: {valgt_pos}")
            
            fig = px.bar(
                df_alle, 
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
                height=hoejde_graf,
                margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- 6. INTERAKTIV SPILLERSØGNING OG INDIVIDUELLE TAL ---
            st.markdown("<hr>", unsafe_allow_html=True)
            st.subheader("🔍 Find specifik spiller og se detaljerede tal")
            
            # Sorterede navne til dropdown-menuen
            spillere_liste = sorted(df['full_name'].dropna().unique())
            valgt_spiller_navn = st.selectbox("Søg efter eller vælg en spiller", spillere_liste)
            
            if valgt_spiller_navn:
                spiller_data = df[df['full_name'] == valgt_spiller_navn].iloc[0]
                
                # Præsentation af spilleren
                st.markdown(f"""
                    <div class="score-card">
                        <div class="pos-title">{spiller_data['full_name']}</div>
                        <div style="font-size: 16px; color: #555;">Klub: <b>{spiller_data['team_name']}</b> | Samlet Performance Score ({valgt_pos}): <b>{spiller_data[score_col]}</b></div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Visning af de individuelle metrics der indgår i scoren
                st.write(f"**Underliggende P90-metrics for {valgt_pos}-profilen:**")
                cols = st.columns(len(config['metrics']))
                
                for idx, m_name in enumerate(config['metrics']):
                    metric_vaerdi = spiller_data[m_name]
                    # Formatér procenter pænt
                    visnings_vaerdi = f"{metric_vaerdi:.1f}%" if "pct" in m_name else f"{metric_vaerdi:.2f}"
                    
                    with cols[idx]:
                        st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-val">{visnings_vaerdi}</div>
                                <div class="stat-lbl">{config['labels'][idx]}</div>
                                <div style="font-size:10px; color:#999; margin-top:2px;">Vægt: {config['weights'][idx]}</div>
                            </div>
                        """, unsafe_allow_html=True)

        else:
            st.info(f"Ingen spillere fundet i systemet med de angivne kriterier for sæsonen {SOGT_SAESON}.")

if __name__ == "__main__":
    vis_side()
