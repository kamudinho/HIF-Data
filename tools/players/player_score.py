import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys
import os

# Sikrer at Python kan finde data_load, selvom denne fil ligger i 'data'-mappen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake-databasen.")
        return

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

    # --- 1. FILTRE OG KONFIGURATION ---
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

    # --- 2. INDLÆS OG VALIDER CSV-FILEN FØRST (GROUND TRUTH) ---
    aktuel_fil_sti = os.path.abspath(__file__)
    projekt_rod = os.path.dirname(aktuel_fil_sti)
    
    # Kravl op i hierarkiet for at finde rodmappen med data-undermappen
    for _ in range(5):
        if os.path.exists(os.path.join(projekt_rod, 'data')):
            break
        projekt_rod = os.path.dirname(projekt_rod)
        
    overskriv_sti = os.path.join(projekt_rod, 'data', 'players', 'spiller_overskrivning.csv')
    
    if not os.path.exists(overskriv_sti):
        st.error(f"Kritisk fejl: CSV-filen med spillere kunne ikke findes på stien: {overskriv_sti}")
        return

    try:
        df_csv = pd.read_csv(overskriv_sti)
        df_csv.columns = df_csv.columns.str.lower().str.strip()
        
        # Sørg for at de nødvendige kolonner findes i din CSV
        # Understøtter både 'player_wyid' / 'wyid' og 'full_name' / 'navn' samt 'specific_position' / 'position'
        df_csv = df_csv.rename(columns={
            'wyid': 'player_wyid',
            'navn': 'full_name',
            'position': 'specific_position'
        })
        
        nødvendige_kolonner = ['player_wyid', 'full_name', 'specific_position']
        if not all(col in df_csv.columns for col in nødvendige_kolonner):
            st.error(f"CSV-filen skal indeholde kolonnerne: {nødvendige_kolonner}")
            return
            
        # Typecast ID'er og fjern dubletter
        df_csv['player_wyid'] = df_csv['player_wyid'].astype(int)
        csv_spiller_ids = df_csv['player_wyid'].tolist()
        
    except Exception as e:
        st.error(f"Fejl ved indlæsning af spillernes CSV-fil: {e}")
        return

    if not csv_spiller_ids:
        st.warning("CSV-filen er tom eller indeholder ingen gyldige spiller-ID'er.")
        return

    # Omdan ID'erne til SQL-venlig tuple/liste
    sql_player_ids_str = f"({', '.join(map(str, csv_spiller_ids))})"

    # --- 3. SQL DATAFETCH (KUN FOR SPILLERE I CSV-FILEN) ---
    with st.spinner("Henter og beregner live-data fra Snowflake..."):
        # Hent minutter og tjek om spilleren er aktiv i Hvidovre i 2026
        sql_minutter = f"""
            WITH hvidovre_2026_spillere AS (
                SELECT DISTINCT m_tot.PLAYER_WYID
                FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL m_tot
                JOIN {DB}.WYSCOUT_MATCHES m ON m_tot.MATCH_WYID = m.MATCH_WYID
                JOIN {DB}.WYSCOUT_PLAYERS p ON m_tot.PLAYER_WYID = p.PLAYER_WYID
                WHERE p.CURRENTTEAM_WYID = {HVIDOVRE_TEAM_WYID}
                  AND m.DATE >= '2026-01-01'
                  AND m_tot.MINUTESONFIELD > 0
            )
            SELECT 
                m_total.PLAYER_WYID,
                SUM(CASE WHEN m_total.COMPETITION_WYID = {valgt_liga} THEN m_total.MINUTESONFIELD ELSE 0 END) as total_minutes,
                MAX(CASE WHEN h26.PLAYER_WYID IS NOT NULL THEN 1 ELSE 0 END) as is_active_hvidovre
            FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL m_total
            LEFT JOIN hvidovre_2026_spillere h26 ON m_total.PLAYER_WYID = h26.PLAYER_WYID
            WHERE m_total.PLAYER_WYID IN {sql_player_ids_str}
            GROUP BY m_total.PLAYER_WYID
            HAVING SUM(CASE WHEN m_total.COMPETITION_WYID = {valgt_liga} THEN m_total.MINUTESONFIELD ELSE 0 END) >= 150
        """
        
        # Hent P90 statistikker samt klubnavne
        sql_stats = f"""
            SELECT 
                p.PLAYER_WYID,
                COALESCE(t.OFFICIALNAME, 'Ukendt Klub') as TEAM_NAME,
                p.CURRENTTEAM_WYID as CURRENT_TEAM_WYID,
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
            LEFT JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
            JOIN {DB}.WYSCOUT_SEASONS seas ON s.SEASON_WYID = seas.SEASON_WYID
            WHERE p.PLAYER_WYID IN {sql_player_ids_str}
              AND seas.SEASONNAME = '{SOGT_SAESON}'
            GROUP BY p.PLAYER_WYID, t.OFFICIALNAME, p.CURRENTTEAM_WYID
        """
        
        df_minutter = conn.query(sql_minutter)
        df_stats = conn.query(sql_stats)
        
        if df_minutter is not None and df_stats is not None and not df_stats.empty and not df_minutter.empty:
            df_minutter.columns = df_minutter.columns.str.lower()
            df_stats.columns = df_stats.columns.str.lower()
            
            # Splejs databasens stats og minutter sammen
            db_df = pd.merge(df_stats, df_minutter, on='player_wyid', how='inner')
            db_df['player_wyid'] = db_df['player_wyid'].astype(int)
            
            # --- 4. SAMMENKOBLING MED CSV (STUERS NAVN OG POSITION HERFRA) ---
            # Vi fletter vores database-stats over på listen fra CSV, så CSV'ens data har førsteprioritet
            df = pd.merge(df_csv, db_df, on='player_wyid', how='inner')
            
            if df.empty:
                st.info(f"Ingen spillere fra CSV-filen har opnået over 150 minutter i den valgte liga.")
                return

            # Beregn pasningsprocent live
            df['pass_pct'] = (df['successfulpasses'] / df['passes'].replace(0, 1)) * 100

            config = POS_CONFIG[valgt_profil]
            
            # Beregn performance score
            score_col = 'pos_score'
            df[score_col] = 0.0
            for i, m_name in enumerate(config['metrics']):
                weight = config['weights'][i]
                df[score_col] += df[m_name] * weight
            
            df[score_col] = df[score_col].round(1)

            # Oversæt positionen taget direkte fra din CSV
            df['dk_position'] = df['specific_position'].map(POS_TRANSLATIONS).fillna(df['specific_position'])
            df_sorteret = df.sort_values(score_col, ascending=False)
            
            # --- 5. LOGIK: TOP 20 LIGA + 2 BEDSTE REELLE HVIDOVRE ---
            liga_spillere = df_sorteret[df_sorteret['is_active_hvidovre'] == 0]
            hvidovre_spillere = df_sorteret[df_sorteret['is_active_hvidovre'] == 1]
            
            top_20_liga = liga_spillere.head(20)
            top_2_hvidovre = hvidovre_spillere.head(2)
            
            visnings_df = pd.concat([top_20_liga, top_2_hvidovre]).drop_duplicates(subset=['player_wyid'])
            
            if visnings_df.empty:
                st.info("Ingen spillere kvalificerede sig til top-oversigten ud fra de valgte filtre.")
                return
            
            visnings_df = visnings_df.sort_values(score_col, ascending=True)
            visnings_df['visningsnavn'] = visnings_df['full_name']

            # Farve efter om de er aktive Hvidovre-spillere
            farve_liste = [
                '#c11c2e' if row['is_active_hvidovre'] == 1 else '#1b365d'
                for _, row in visnings_df.iterrows()
            ]

            # --- 6. SPLIT-SCREEN LAYOUT ---
            rude_venstre, rude_hoejre = st.columns([1.1, 0.9])

            # RUDE 1 (VENSTRE): Scoreboard
            with rude_venstre:
                st.subheader("Performance Scoreboard")
                
                hoejde_graf = max(500, len(visnings_df) * 26)
                
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
                
                valgt_klik = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

            # RUDE 2 (HØJRE): Spiller-detaljer
            with rude_hoejre:
                st.subheader("Spiller-detaljer")
                
                valgt_spiller_data = None
                
                if valgt_klik and "selection" in valgt_klik and valgt_klik["selection"]["points"]:
                    klikket_navn = valgt_klik["selection"]["points"][0]["y"]
                    valgt_spiller_data = df[df['full_name'] == klikket_navn].iloc[0]
                elif not visnings_df.empty:
                    bedste_spiller_id = visnings_df.sort_values(score_col, ascending=False).iloc[0]['player_wyid']
                    valgt_spiller_data = df[df['player_wyid'] == bedste_spiller_id].iloc[0]

                if valgt_spiller_data is not None:
                    st.markdown(f"""
                        <div class="score-card">
                            <div class="pos-title">{valgt_spiller_data['full_name']}</div>
                            <div style="font-size: 14px; color: #555; line-height: 1.5;">
                                Klub: <b>{valgt_spiller_data['team_name']}</b><br>
                                Position (Fra din CSV): <b>{valgt_spiller_data['dk_position']}</b><br>
                                Spillede minutter (i ligaen): <b>{int(valgt_spiller_data['total_minutes'])} min.</b><br>
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
            st.info(f"Fandt ingen aktive stats eller minutter for de spillere, der er defineret i din CSV-fil ({valgt_profil}).")

if __name__ == "__main__":
    vis_side()
