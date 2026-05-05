import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn

def vis_side():
    # CSS styling af metrics-bokse og overskrifter (Uden ikoner)
    st.markdown("""
        <style>
        .score-card { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #df003b; margin-bottom: 15px; }
        .pos-title { font-size: 22px; font-weight: bold; color: #1E1E1E; margin-bottom: 2px; }
        .metric-row { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            padding: 10px 15px; 
            background-color: #ffffff; 
            border: 1px solid #e0e0e0; 
            border-radius: 6px; 
            margin-bottom: 8px; 
        }
        .metric-label { font-weight: 500; color: #333; font-size: 14px; }
        .metric-value { font-weight: bold; color: #df003b; font-size: 16px; }
        .metric-weight { font-size: 11px; color: #888; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    DB = "KLUB_HVIDOVREIF.AXIS"
    SOGT_SAESON = "2025/2026"
    HVIDOVRE_TEAM_WYID = 7490  # Hvidovre IF ID

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

    # --- 2. FILTRE ---
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
    # Vi beregner spillernes samlede spilletid i den valgte liga/sæson via WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL
    # Og vi finder spillerens mest spillede specifikke position via WYSCOUT_MATCHADVANCEDPLAYERSTATS_BASE
    with st.spinner("Henter og beregner Wyscout-data..."):
        sql = f"""
        WITH player_minutes AS (
            SELECT 
                PLAYER_WYID,
                SUM(MINUTESONFIELD) as total_minutes
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL
            WHERE COMPETITION_WYID = {valgt_liga}
            GROUP BY PLAYER_WYID
            HAVING SUM(MINUTESONFIELD) >= 270
        ),
        player_primary_position AS (
            SELECT 
                PLAYER_WYID,
                POSITION1NAME as primary_position,
                ROW_NUMBER() OVER (PARTITION BY PLAYER_WYID ORDER BY COUNT(*) DESC) as pos_rank
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_BASE
            WHERE COMPETITION_WYID = {valgt_liga}
              AND SEASON_WYID = (SELECT DISTINCT SEASON_WYID FROM {DB}.WYSCOUT_SEASONS WHERE SEASONNAME = '{SOGT_SAESON}' LIMIT 1)
            GROUP BY PLAYER_WYID, POSITION1NAME
        )
        SELECT 
            p.PLAYER_WYID,
            COALESCE(
                NULLIF(TRIM(p.FIRSTNAME || ' ' || p.LASTNAME), ''), 
                p.SHORTNAME
            ) as FULL_NAME, 
            t.OFFICIALNAME as TEAM_NAME,
            p.CURRENTTEAM_WYID as TEAM_WYID,
            pm.total_minutes,
            COALESCE(ppp.primary_position, 'Ukendt Position') as SPECIFIC_POSITION,
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
            AVG(s.AERIALDUELS) AS AERIALDUELSWON,
            AVG(s.DANGEROUSOWNHALFLOSSES) as DANGEROUSOWNHALFLOSSES,
            AVG(s.ASSISTS) as ASSISTS
        FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE s
        JOIN {DB}.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
        JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
        JOIN {DB}.WYSCOUT_SEASONS seas ON s.SEASON_WYID = seas.SEASON_WYID
        JOIN player_minutes pm ON p.PLAYER_WYID = pm.PLAYER_WYID
        LEFT JOIN player_primary_position ppp ON p.PLAYER_WYID = ppp.PLAYER_WYID AND ppp.pos_rank = 1
        WHERE s.COMPETITION_WYID = {valgt_liga}
          AND seas.SEASONNAME = '{SOGT_SAESON}'
        GROUP BY p.PLAYER_WYID, p.FIRSTNAME, p.LASTNAME, p.SHORTNAME, t.OFFICIALNAME, p.CURRENTTEAM_WYID, pm.total_minutes, ppp.primary_position
        """
        
        raw_df = conn.query(sql)
        
        if raw_df is not None and not raw_df.empty:
            raw_df.columns = raw_df.columns.str.lower()
            
            # --- 4. BEREGNING AF PASNINGSPROCENT ---
            raw_df['pass_pct'] = (raw_df['successfulpasses'] / raw_df['passes'].replace(0, 1)) * 100

            # Find den valgte profilkonfiguration
            config = POS_CONFIG[valgt_pos]
            
            # Beregn performance score pr. række
            score_col = 'pos_score'
            raw_df[score_col] = 0.0
            for i, m_name in enumerate(config['metrics']):
                weight = config['weights'][i]
                raw_df[score_col] += raw_df[m_name] * weight
            
            # --- 5. CLEAN PANDAS GROUPBY ---
            agg_dict = {
                'full_name': 'first',
                'team_name': 'first',
                'team_wyid': 'first',
                'total_minutes': 'first',
                'specific_position': 'first',
                score_col: 'first'
            }
            
            for m_name in config['metrics']:
                agg_dict[m_name] = 'first'
                
            df = raw_df.groupby('player_wyid', as_index=False).agg(agg_dict)
            df[score_col] = df[score_col].round(1)
            
            df['visningsnavn'] = df['full_name']
            df_alle = df.sort_values(score_col, ascending=True)

            # Tildel farver (Hvidovre = Blå, andre = Rød)
            farve_liste = [
                '#1b365d' if int(row['team_wyid']) == HVIDOVRE_TEAM_WYID else '#c11c2e'
                for _, row in df_alle.iterrows()
            ]

            # --- 6. SPLIT-SCREEN LAYOUT ---
            rude_venstre, rude_hoejre = st.columns([1.1, 0.9])

            # RUDE 1 (VENSTRE): Scoreboard
            with rude_venstre:
                st.subheader(f"{valgt_pos} Scoreboard")
                
                hoejde_graf = max(500, len(df_alle) * 26)
                
                fig = px.bar(
                    df_alle, 
                    x=score_col, 
                    y='visningsnavn', 
                    orientation='h',
                    text=score_col,
                    template='plotly_white'
                )
                
                fig.update_traces(
                    marker_color=farve_liste, 
                    textposition='inside',   
                    textfont=dict(color='white', size=11, family="Arial"), 
                    insidetextanchor='end',  
                    cliponaxis=False
                )
                
                fig.update_layout(
                    yaxis={'categoryorder':'total ascending', 'title': None}, 
                    xaxis={'title': f"{valgt_pos} Performance Score", 'showgrid': False},
                    showlegend=False, 
                    height=hoejde_graf,
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)

            # RUDE 2 (HØJRE): Spiller-vælger og detaljerede metrics
            with rude_hoejre:
                st.subheader("Søg Spiller")
                
                spillere_liste = sorted(df['full_name'].dropna().unique())
                valgt_spiller_navn = st.selectbox("Vælg eller skriv spillernavn:", spillere_liste)
                
                if valgt_spiller_navn:
                    spiller_data = df[df['full_name'] == valgt_spiller_navn].iloc[0]
                    
                    st.markdown(f"""
                        <div class="score-card">
                            <div class="pos-title">{spiller_data['full_name']}</div>
                            <div style="font-size: 14px; color: #555; line-height: 1.5;">
                                Klub: <b>{spiller_data['team_name']}</b><br>
                                Detaljeret Position: <b>{spiller_data['specific_position']}</b><br>
                                Spillede minutter: <b>{int(spiller_data['total_minutes'])} min.</b><br>
                                Samlet Score ({valgt_pos}): <b>{spiller_data[score_col]}</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.write(f"**Underliggende P90-værdier ({valgt_pos}):**")
                    
                    for idx, m_name in enumerate(config['metrics']):
                        metric_vaerdi = spiller_data[m_name]
                        visnings_vaerdi = f"{metric_vaerdi:.1f}%" if "pct" in m_name else f"{metric_vaerdi:.2f}"
                        
                        st.markdown(f"""
                            <div class="metric-row">
                                <div>
                                    <span class="metric-label">{config['labels'][idx]}</span>
                                    <span class="metric-weight">(Vægt: {config['weights'][idx]})</span>
                                </div>
                                <div class="metric-value">{visnings_vaerdi}</div>
                            </div>
                        """, unsafe_allow_html=True)

        else:
            st.info(f"Ingen spillere med over 270 minutter fundet i systemet med de angivne kriterier for sæsonen {SOGT_SAESON}.")

if __name__ == "__main__":
    vis_side()
