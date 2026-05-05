import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data.data_load import _get_snowflake_conn

def vis_side():
    # CSS styling af metrics-bokse og overskrifter
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

    # --- 1. MAPPING MOD DE OFFICIELLE KOLONNER (ROLECODE3 & ROLENAME) ---
    ROLE_MAPPING = {
        "Forsvar": "DEF",
        "Midtbane": "MID",
        "Angriber": "FWD"
    }

    POS_TRANSLATIONS = {
        "Center Back": "Midterforsvarer",
        "Left Back": "Venstre Back",
        "Right Back": "Højre Back",
        "Left Wing Back": "Venstre Wingback",
        "Right Wing Back": "Højre Wingback",
        "Defensive Midfielder": "Defensiv Midtbane",
        "Central Midfielder": "Central Midtbane",
        "Attacking Midfielder": "Offensiv Midtbane",
        "Left Midfielder": "Venstre Midtbane",
        "Right Midfielder": "Højre Midtbane",
        "Striker": "Angriber / Centerforward",
        "Left Winger": "Venstre Winger",
        "Right Winger": "Højre Winger",
        "Second Striker": "Hængende Angriber",
        "Ukendt Position": "Ukendt Position",
        "DEF": "Forsvarer",
        "MID": "Midtbanespiller",
        "FWD": "Angrebsspiller"
    }

    # --- 2. HENT LIGAER DYNAMISK ---
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

    # --- 3. FILTRE ---
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
    
    valgt_profil = col1.selectbox("Vælg Kategori", list(POS_CONFIG.keys()))
    
    valgt_liga = col2.selectbox(
        "Vælg Liga", 
        ligaer, 
        format_func=lambda x: LIGA_MAP.get(x, f"Liga ID: {x}")
    )

    sogt_role_code = ROLE_MAPPING[valgt_profil]

    # --- 4. DATAFETCH ---
    with st.spinner("Henter og beregner Wyscout-data..."):
        sql = f"""
        WITH player_minutes AS (
            SELECT 
                t_stats.PLAYER_WYID,
                SUM(t_stats.MINUTESONFIELD) as total_minutes
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL t_stats
            JOIN {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_BASE b_stats 
              ON t_stats.MATCH_WYID = b_stats.MATCH_WYID 
             AND t_stats.PLAYER_WYID = b_stats.PLAYER_WYID
            JOIN {DB}.WYSCOUT_SEASONS seas ON b_stats.SEASON_WYID = seas.SEASON_WYID
            WHERE t_stats.COMPETITION_WYID = {valgt_liga}
              AND seas.SEASONNAME = '{SOGT_SAESON}'
            GROUP BY t_stats.PLAYER_WYID
            HAVING SUM(t_stats.MINUTESONFIELD) >= 270
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
            COALESCE(p.ROLENAME, p.ROLECODE3) as SPECIFIC_POSITION,
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
        WHERE s.COMPETITION_WYID = {valgt_liga}
          AND seas.SEASONNAME = '{SOGT_SAESON}'
          AND p.ROLECODE3 = '{sogt_role_code}'
        GROUP BY p.PLAYER_WYID, p.FIRSTNAME, p.LASTNAME, p.SHORTNAME, t.OFFICIALNAME, p.CURRENTTEAM_WYID, pm.total_minutes, p.ROLENAME, p.ROLECODE3
        """
        
        raw_df = conn.query(sql)
        
        if raw_df is not None and not raw_df.empty:
            raw_df.columns = raw_df.columns.str.lower()
            
            # --- 5. BEREGNING AF PASNINGSPROCENT ---
            raw_df['pass_pct'] = (raw_df['successfulpasses'] / raw_df['passes'].replace(0, 1)) * 100

            config = POS_CONFIG[valgt_profil]
            
            # Beregn performance score
            score_col = 'pos_score'
            raw_df[score_col] = 0.0
            for i, m_name in enumerate(config['metrics']):
                weight = config['weights'][i]
                raw_df[score_col] += raw_df[m_name] * weight
            
            # --- 6. CLEAN PANDAS GROUPBY ---
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
            
            # Sorter efter score (højeste først)
            df_sorteret = df.sort_values(score_col, ascending=False)
            
            # --- NY LOGIK: TOP 20 + 2 BEDSTE FRA HVIDOVRE ---
            # 1. Tag de 20 bedste fra ligaen
            top_20_liga = df_sorteret.head(20)
            
            # 2. Tag de 2 bedste fra Hvidovre IF (team_wyid == 7490)
            hvidovre_spillere = df_sorteret[df_sorteret['team_wyid'] == HVIDOVRE_TEAM_WYID]
            top_2_hvidovre = hvidovre_spillere.head(2)
            
            # 3. Kombiner dem (og fjern eventuelle dubletter, hvis Hvidovre-spillerne allerede er i top 20)
            visnings_df = pd.concat([top_20_liga, top_2_hvidovre]).drop_duplicates(subset=['player_wyid'])
            
            # Sorter til grafen (stigende score, så de bedste er øverst i det liggende søjlediagram)
            visnings_df = visnings_df.sort_values(score_col, ascending=True)
            
            # Oversæt position
            visnings_df['dk_position'] = visnings_df['specific_position'].map(POS_TRANSLATIONS).fillna(visnings_df['specific_position'])
            visnings_df['visningsnavn'] = visnings_df['full_name']

            # Tildel farver (Hvidovre = Blå, andre = Rød)
            farve_liste = [
                '#1b365d' if int(row['team_wyid']) == HVIDOVRE_TEAM_WYID else '#c11c2e'
                for _, row in visnings_df.iterrows()
            ]

            # --- 7. SPLIT-SCREEN LAYOUT ---
            rude_venstre, rude_hoejre = st.columns([1.1, 0.9])

            # RUDE 1 (VENSTRE): Scoreboard
            with rude_venstre:
                st.subheader(f"Scoreboard: Top 20 & Hvidovre Top 2")
                
                hoejde_graf = max(500, len(visnings_df) * 26)
                
                fig = px.bar(
                    visnings_df, 
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
                    xaxis={'title': f"{valgt_profil} Performance Score", 'showgrid': False},
                    showlegend=False, 
                    height=hoejde_graf,
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)

            # RUDE 2 (HØJRE): Spiller-vælger (bruger det fulde datasæt df, så man stadig kan søge på alle spillere)
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
                                Primær Position: <b>{spiller_data['specific_position'].map(POS_TRANSLATIONS).fillna(spiller_data['specific_position'])}</b><br>
                                Spillede minutter (2025/2026): <b>{int(spiller_data['total_minutes'])} min.</b><br>
                                Samlet Score ({valgt_profil}): <b>{spiller_data[score_col]}</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.write(f"**Underliggende P90-værdier ({valgt_profil}):**")
                    
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
            st.info(f"Ingen spillere med over 270 minutter fundet med rollen '{valgt_profil}' i den valgte liga for sæsonen {SOGT_SAESON}.")

if __name__ == "__main__":
    vis_side()
