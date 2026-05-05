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

    # --- 1. FILTRE ---
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
    
    # Hent ligaer dynamisk
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
    
    valgt_liga = col2.selectbox(
        "Vælg Liga", 
        ligaer, 
        format_func=lambda x: LIGA_MAP.get(x, f"Liga ID: {x}")
    )

    # Backup-mapping til kampspecifikke positioner
    if valgt_profil == "Forsvar":
        pos_fallback_filter = "b_stats.POSITION1CODE IN ('CB', 'LB', 'RB', 'LWB', 'RWB')"
        role_code = "DEF"
    elif valgt_profil == "Midtbane":
        pos_fallback_filter = "b_stats.POSITION1CODE IN ('DMF', 'CMF', 'AMF', 'LM', 'RM')"
        role_code = "MID"
    else:  # Angriber
        pos_fallback_filter = "b_stats.POSITION1CODE IN ('CF', 'LWF', 'RWF', 'SS')"
        role_code = "FWD"

    # --- 2. DATAFETCH ---
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
            JOIN {DB}.WYSCOUT_PLAYERS p ON t_stats.PLAYER_WYID = p.PLAYER_WYID
            JOIN {DB}.WYSCOUT_SEASONS seas ON b_stats.SEASON_WYID = seas.SEASON_WYID
            WHERE (t_stats.COMPETITION_WYID = {valgt_liga} OR p.CURRENTTEAM_WYID = {HVIDOVRE_TEAM_WYID})
              AND seas.SEASONNAME = '{SOGT_SAESON}'
            GROUP BY t_stats.PLAYER_WYID
            HAVING SUM(t_stats.MINUTESONFIELD) >= 150
        ),
        most_played_position AS (
            SELECT 
                b_stats.PLAYER_WYID,
                b_stats.POSITION1NAME as MATCH_POS_NAME,
                ROW_NUMBER() OVER (PARTITION BY b_stats.PLAYER_WYID ORDER BY COUNT(*) DESC) as rnk
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_BASE b_stats
            JOIN {DB}.WYSCOUT_SEASONS seas ON b_stats.SEASON_WYID = seas.SEASON_WYID
            WHERE seas.SEASONNAME = '{SOGT_SAESON}'
              AND b_stats.POSITION1NAME IS NOT NULL
            GROUP BY b_stats.PLAYER_WYID, b_stats.POSITION1NAME
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
            COALESCE(p.ROLENAME, mpp.MATCH_POS_NAME, 'Ukendt Position') as SPECIFIC_POSITION,
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
        LEFT JOIN most_played_position mpp ON p.PLAYER_WYID = mpp.PLAYER_WYID AND mpp.rnk = 1
        JOIN {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_BASE b_stats 
          ON s.PLAYER_WYID = b_stats.PLAYER_WYID 
         AND s.SEASON_WYID = b_stats.SEASON_WYID
        WHERE (s.COMPETITION_WYID = {valgt_liga} OR p.CURRENTTEAM_WYID = {HVIDOVRE_TEAM_WYID})
          AND seas.SEASONNAME = '{SOGT_SAESON}'
          AND (p.ROLECODE3 = '{role_code}' OR (COALESCE(p.ROLECODE3, '') = '' AND {pos_fallback_filter}))
        GROUP BY p.PLAYER_WYID, p.FIRSTNAME, p.LASTNAME, p.SHORTNAME, t.OFFICIALNAME, p.CURRENTTEAM_WYID, pm.total_minutes, p.ROLENAME, mpp.MATCH_POS_NAME, p.ROLECODE3
        """
        
        raw_df = conn.query(sql)
        
        if raw_df is not None and not raw_df.empty:
            raw_df.columns = raw_df.columns.str.lower()
            
            # --- 3. BEREGNING AF PASNINGSPROCENT ---
            raw_df['pass_pct'] = (raw_df['successfulpasses'] / raw_df['passes'].replace(0, 1)) * 100

            config = POS_CONFIG[valgt_profil]
            
            # Beregn performance score
            score_col = 'pos_score'
            raw_df[score_col] = 0.0
            for i, m_name in enumerate(config['metrics']):
                weight = config['weights'][i]
                raw_df[score_col] += raw_df[m_name] * weight
            
            # --- 4. CLEAN PANDAS GROUPBY ---
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
            
            df['dk_position'] = df['specific_position'].map(POS_TRANSLATIONS).fillna(df['specific_position'])
            df_sorteret = df.sort_values(score_col, ascending=False)
            
            # --- 5. LOGIK: TOP 20 FRA LIGAEN + 2 BEDSTE FRA HVIDOVRE ---
            liga_spillere = df_sorteret[df_sorteret['player_wyid'].isin(
                raw_df[raw_df['team_wyid'] != HVIDOVRE_TEAM_WYID]['player_wyid']
            ) | (df_sorteret['team_wyid'] == HVIDOVRE_TEAM_WYID)]
            
            top_20_liga = liga_spillere[liga_spillere['team_wyid'] != HVIDOVRE_TEAM_WYID].head(20)
            hvidovre_spillere = df_sorteret[df_sorteret['team_wyid'] == HVIDOVRE_TEAM_WYID]
            top_2_hvidovre = hvidovre_spillere.head(2)
            
            visnings_df = pd.concat([top_20_liga, top_2_hvidovre]).drop_duplicates(subset=['player_wyid'])
            
            # Sorter så de bedste spillere lægges i toppen af det liggende søjlediagram
            visnings_df = visnings_df.sort_values(score_col, ascending=True)
            visnings_df['visningsnavn'] = visnings_df['full_name']

            # Hvidovre = Rød (#c11c2e), Andre klubber = Blå (#1b365d)
            farve_liste = [
                '#c11c2e' if int(row['team_wyid']) == HVIDOVRE_TEAM_WYID else '#1b365d'
                for _, row in visnings_df.iterrows()
            ]

            # --- 6. SPLIT-SCREEN LAYOUT ---
            rude_venstre, rude_hoejre = st.columns([1.1, 0.9])

            # RUDE 1 (VENSTRE): Scoreboard
            with rude_venstre:
                st.subheader("Performance Scoreboard")
                
                hoejde_graf = max(500, len(visnings_df) * 26)
                
                # Plotly med klik-events aktiveret
                fig = px.bar(
                    visnings_df, 
                    x=score_col, 
                    y='visningsnavn', 
                    orientation='h',
                    text=score_col,
                    template='plotly_white',
                    custom_data=['player_wyid']
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
                    margin=dict(l=10, r=10, t=10, b=10),
                    clickmode='event+select'
                )
                
                # Registrer kliks på søjlerne
                valgt_klik = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

            # RUDE 2 (HØJRE): Spiller-detaljer (Uden dropdown / søgetekst)
            with rude_hoejre:
                st.subheader("Spiller-detaljer")
                
                # Find ud af, hvilken spiller der skal vises:
                # 1. Hvis brugeren har klikket på en spiller i grafen
                # 2. Ellers tager vi den absolut bedste spiller på listen som standard
                valgt_spiller_data = None
                
                if valgt_klik and "selection" in valgt_klik and valgt_klik["selection"]["points"]:
                    klikket_navn = valgt_klik["selection"]["points"][0]["y"]
                    valgt_spiller_data = df[df['full_name'] == klikket_navn].iloc[0]
                else:
                    # Standard: Vis den bedst rangerede spiller fra visnings_df
                    bedste_spiller_id = visnings_df.sort_values(score_col, ascending=False).iloc[0]['player_wyid']
                    valgt_spiller_data = df[df['player_wyid'] == bedste_spiller_id].iloc[0]

                if valgt_spiller_data is not None:
                    st.markdown(f"""
                        <div class="score-card">
                            <div class="pos-title">{valgt_spiller_data['full_name']}</div>
                            <div style="font-size: 14px; color: #555; line-height: 1.5;">
                                Klub: <b>{valgt_spiller_data['team_name']}</b><br>
                                Position (Wyscout / Kamp-data): <b>{valgt_spiller_data['dk_position']}</b><br>
                                Spillede minutter (2025/2026): <b>{int(valgt_spiller_data['total_minutes'])} min.</b><br>
                                Samlet Score ({valgt_profil}): <b>{valgt_spiller_data[score_col]}</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.write(f"**Underliggende P90-værdier ({valgt_profil}):**")
                    
                    for idx, m_name in enumerate(config['metrics']):
                        metric_vaerdi = valgt_spiller_data[m_name]
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
            st.info(f"Ingen spillere med over 150 minutter fundet med rollen '{valgt_profil}' i den valgte liga for sæsonen {SOGT_SAESON}.")

if __name__ == "__main__":
    vis_side()
