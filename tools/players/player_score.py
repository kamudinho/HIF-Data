import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys
import os

# Sikrer at Python kan finde data_load, selvom denne fil ligger i 'data'-mappen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.data_load import _get_snowflake_conn

def map_til_hovedkategori(position_str):
    if not isinstance(position_str, str):
        return "Ukendt"
    
    pos = position_str.strip().lower()
    
    # MÅLMAND
    if any(x in pos for x in ["målmand", "goalkeeper", "keeper", "gk"]):
        return "Målmand"
        
    # FORSVARSSPILLER
    if any(x in pos for x in ["forsvar", "defender", "cb", "lb", "rb", "lwb", "rwb", "stopper", "back", "def"]):
        return "Forsvarsspiller"
        
    # ANGRIBER
    if any(x in pos for x in ["angriber", "forward", "striker", "cf", "wf", "ss", "9'er", "fwd", "frontløber", "winger", "wing"]):
        return "Angriber"
        
    # MIDTBANESPILLER
    if any(x in pos for x in ["midtbane", "midfielder", "dmf", "cmf", "amf", "lm", "rm", "kant", "mid", "6'er", "8'er", "10'er"]):
        return "Midtbanespiller"
        
    return "Ukendt"

def vis_side():
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
    HVIDOVRE_TEAM_WYID = 7490
    
    TILLADTE_LIGAER = (335, 328, 329, 43319, 331, 1305)

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
        "Goalkeeper": "Målmand",
        "Defender": "Forsvarsspiller",
        "Midfielder": "Midtbanespiller",
        "Forward": "Angrebsspiller"
    }

    POS_CONFIG = {
        "Angriber": {
            "metrics": ["goals", "xg", "shots", "touchinbox", "dribbles", "assists"],
            "weights": [6.0, 4.0, 3.8, 2.4, 1.2, 2.0],
            "labels": ["Mål", "xG", "Skud", "Berøringer i felt", "Driblinger", "Assists"]
        },
        "Midtbanespiller": {
            "metrics": ["pass_pct", "keypasses", "interceptions", "xgassist", "slidingtackles", "progressiverun"],
            "weights": [8.0, 4.5, 3.0, 4.0, 2.0, 1.5],
            "labels": ["Pasnings %", "Key Passes", "Interceptions", "xA", "Glidende Tacklinger", "Progressive løb"]
        },
        "Forsvarsspiller": {
            "metrics": ["interceptions", "defensiveduelswon", "clearances", "aerialduelswon", "pass_pct", "dangerousownhalflosses"],
            "weights": [5.0, 4.0, 3.5, 4.0, 2.5, -3.0], 
            "labels": ["Interceptions", "Vundne Def. Dueller", "Clearinger", "Vundne Luftdueller", "Pasnings %", "Farlige Boldtab (Egen banehalvdel)"]
        },
        "Målmand": {
            "metrics": ["pass_pct", "clearances"],
            "weights": [5.0, 5.0],
            "labels": ["Pasnings %", "Clearinger"]
        }
    }

    # --- 1. INDLÆS CSV-FIL MED ENCODING-TJEK (Løser 'Thor H√∏lholt' problemet) ---
    aktuel_fil_sti = os.path.abspath(__file__)
    projekt_rod = os.path.dirname(aktuel_fil_sti)
    for _ in range(5):
        if os.path.exists(os.path.join(projekt_rod, 'data')):
            break
        projekt_rod = os.path.dirname(projekt_rod)
        
    overskriv_sti = os.path.join(projekt_rod, 'data', 'players', 'spiller_overskrivning.csv')
    
    if not os.path.exists(overskriv_sti):
        st.error(f"Kritisk fejl: CSV-filen kunne ikke findes på stien: {overskriv_sti}")
        return

    df_csv = None
    for enc in ['utf-8-sig', 'latin-1', 'utf-8', 'cp1252']:
        try:
            df_csv = pd.read_csv(overskriv_sti, encoding=enc)
            # Tjek om der er mærkelige tegn i indlæsningen
            if not df_csv.empty and not df_csv.iloc[:,1].astype(str).str.contains('√').any():
                break
        except Exception:
            continue

    if df_csv is None:
        st.error("Kunne ikke indlæse CSV-filen korrekt.")
        return

    df_csv.columns = df_csv.columns.str.lower().str.strip()
    df_csv = df_csv.rename(columns={
        'wyid': 'player_wyid',
        'navn': 'full_name',
        'position': 'specific_position'
    })
    df_csv['player_wyid'] = df_csv['player_wyid'].astype(int)
    df_csv['hovedkategori'] = df_csv['specific_position'].apply(map_til_hovedkategori)

    # --- 2. DYNAMISKE FILTRE ---
    col1, col2, col3 = st.columns(3)
    valgt_hovedkategori = col1.selectbox("Vælg Kategori", list(POS_CONFIG.keys()))
    
    # Hent specifikke positioner direkte fra databasen for at undgå at være begrænset af dit CSV-ark
    specifikke_muligheder = sorted(df_csv[df_csv['hovedkategori'] == valgt_hovedkategori]['specific_position'].dropna().unique().tolist())
    visnings_positioner_map = {pos: POS_TRANSLATIONS.get(pos, pos) for pos in specifikke_muligheder}
    
    valgt_specifik_visning = col2.selectbox(
        "Vælg Specifik Position", 
        [f"Alle {valgt_hovedkategori}e" if valgt_hovedkategori != "Målmand" else "Alle Målmænd"] + list(visnings_positioner_map.values())
    )
    
    faktisk_specifik_valg = None
    for eng_pos, dk_pos in visnings_positioner_map.items():
        if dk_pos == valgt_specifik_visning:
            faktisk_specifik_valg = eng_pos
            break

    LIGA_VALGMULIGHEDER = {
        "alle": "Alle turneringer",
        328: "Betinia Ligaen",
        335: "Superligaen",
        329: "2. division",
        43319: "3. division",
        331: "Oddset Pokalen",
        1305: "U19 Ligaen"
    }
    valgt_liga_nøgle = col3.selectbox("Vælg Turnering", list(LIGA_VALGMULIGHEDER.keys()), format_func=lambda x: LIGA_VALGMULIGHEDER[x])

    # --- 3. RETTET SQL-FORESPØRGSEL (Løser minut-mangedobling) ---
    if valgt_liga_nøgle == "alle":
        liga_betingelse_total = f"m_tot.COMPETITION_WYID IN {TILLADTE_LIGAER}"
        liga_betingelse_stats = f"s.COMPETITION_WYID IN {TILLADTE_LIGAER}"
    else:
        liga_betingelse_total = f"m_tot.COMPETITION_WYID = {valgt_liga_nøgle}"
        liga_betingelse_stats = f"s.COMPETITION_WYID = {valgt_liga_nøgle}"

    # SQL filter på specifik position hvis valgt
    pos_betingelse = ""
    if faktisk_specifik_valg:
        pos_betingelse = f"AND p.ROLE_NAME = '{faktisk_specifik_valg}'"
    else:
        # Hvis 'Alle', filter på overordnede roller
        if valgt_hovedkategori == "Målmand":
            pos_betingelse = "AND p.ROLE_NAME IN ('Goalkeeper')"
        elif valgt_hovedkategori == "Forsvarsspiller":
            pos_betingelse = "AND p.ROLE_NAME IN ('Center Back', 'Left Back', 'Right Back', 'Left Wing Back', 'Right Wing Back', 'Defender')"
        elif valgt_hovedkategori == "Midtbanespiller":
            pos_betingelse = "AND p.ROLE_NAME IN ('Defensive Midfielder', 'Central Midfielder', 'Attacking Midfielder', 'Left Midfielder', 'Right Midfielder', 'Midfielder')"
        elif valgt_hovedkategori == "Angriber":
            pos_betingelse = "AND p.ROLE_NAME IN ('Striker', 'Left Winger', 'Right Winger', 'Second Striker', 'Forward')"

    with st.spinner("Henter og beregner live-data..."):
        sql_avanceret = f"""
            WITH minut_beregning AS (
                -- Beregn minutter pr. spiller isoleret for at forhindre mangedobling i JOIN
                SELECT 
                    PLAYER_WYID,
                    SUM(CASE WHEN {liga_betingelse_total} THEN MINUTESONFIELD ELSE 0 END) as total_minutes_selected_liga,
                    SUM(MINUTESONFIELD) as total_minutes_all_ligas
                FROM {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL m_tot
                WHERE m_tot.COMPETITION_WYID IN {TILLADTE_LIGAER}
                GROUP BY PLAYER_WYID
            ),
            hvidovre_spillere_2026 AS (
                SELECT DISTINCT p.PLAYER_WYID
                FROM {DB}.WYSCOUT_PLAYERS p
                JOIN {DB}.WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL m_tot ON p.PLAYER_WYID = m_tot.PLAYER_WYID
                JOIN {DB}.WYSCOUT_MATCHES m ON m_tot.MATCH_WYID = m.MATCH_WYID
                WHERE p.CURRENTTEAM_WYID = {HVIDOVRE_TEAM_WYID}
                  AND m.DATE >= '2026-01-01'
                  AND m_tot.MINUTESONFIELD > 0
            ),
            hvidovre_stats AS (
                SELECT 
                    p.PLAYER_WYID,
                    p.SHORTNAME as FULL_NAME,
                    p.ROLE_NAME as SPECIFIC_POSITION,
                    COALESCE(t.OFFICIALNAME, 'Hvidovre IF') as TEAM_NAME,
                    p.CURRENTTEAM_WYID as CURRENT_TEAM_WYID,
                    COALESCE(m_calc.total_minutes_all_ligas, 0) as total_minutes,
                    1 as is_active_hvidovre,
                    AVG(s.GOALS) as GOALS, AVG(s.XGSHOT) AS XG, AVG(s.SHOTS) as SHOTS,
                    AVG(s.TOUCHINBOX) as TOUCHINBOX, AVG(s.DRIBBLES) as DRIBBLES,
                    AVG(s.PASSES) as PASSES, AVG(s.SUCCESSFULPASSES) as SUCCESSFULPASSES,
                    AVG(s.KEYPASSES) as KEYPASSES, AVG(s.INTERCEPTIONS) as INTERCEPTIONS,
                    AVG(s.XGASSIST) as XGASSIST, AVG(s.SLIDINGTACKLES) as SLIDINGTACKLES,
                    AVG(s.PROGRESSIVERUN) as PROGRESSIVERUN, AVG(s.DEFENSIVEDUELSWON) as DEFENSIVEDUELSWON,
                    AVG(s.CLEARANCES) as CLEARANCES, AVG(s.AERIALDUELS) AS AERIALDUELSWON,
                    AVG(s.DANGEROUSOWNHALFLOSSES) as DANGEROUSOWNHALFLOSSES, AVG(s.ASSISTS) as ASSISTS
                FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE s
                JOIN {DB}.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
                LEFT JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                JOIN {DB}.WYSCOUT_SEASONS seas ON s.SEASON_WYID = seas.SEASON_WYID
                LEFT JOIN minut_beregning m_calc ON p.PLAYER_WYID = m_calc.PLAYER_WYID
                WHERE p.PLAYER_WYID IN (SELECT PLAYER_WYID FROM hvidovre_spillere_2026)
                  AND seas.SEASONNAME = '{SOGT_SAESON}'
                  AND s.COMPETITION_WYID IN {TILLADTE_LIGAER}
                  {pos_betingelse}
                GROUP BY p.PLAYER_WYID, p.SHORTNAME, p.ROLE_NAME, t.OFFICIALNAME, p.CURRENTTEAM_WYID, m_calc.total_minutes_all_ligas
                HAVING COALESCE(m_calc.total_minutes_all_ligas, 0) >= 150
            ),
            liga_stats AS (
                SELECT 
                    p.PLAYER_WYID,
                    p.SHORTNAME as FULL_NAME,
                    p.ROLE_NAME as SPECIFIC_POSITION,
                    COALESCE(t.OFFICIALNAME, 'Ukendt Klub') as TEAM_NAME,
                    p.CURRENTTEAM_WYID as CURRENT_TEAM_WYID,
                    COALESCE(m_calc.total_minutes_selected_liga, 0) as total_minutes,
                    0 as is_active_hvidovre,
                    AVG(s.GOALS) as GOALS, AVG(s.XGSHOT) AS XG, AVG(s.SHOTS) as SHOTS,
                    AVG(s.TOUCHINBOX) as TOUCHINBOX, AVG(s.DRIBBLES) as DRIBBLES,
                    AVG(s.PASSES) as PASSES, AVG(s.SUCCESSFULPASSES) as SUCCESSFULPASSES,
                    AVG(s.KEYPASSES) as KEYPASSES, AVG(s.INTERCEPTIONS) as INTERCEPTIONS,
                    AVG(s.XGASSIST) as XGASSIST, AVG(s.SLIDINGTACKLES) as SLIDINGTACKLES,
                    AVG(s.PROGRESSIVERUN) as PROGRESSIVERUN, AVG(s.DEFENSIVEDUELSWON) as DEFENSIVEDUELSWON,
                    AVG(s.CLEARANCES) as CLEARANCES, AVG(s.AERIALDUELS) AS AERIALDUELSWON,
                    AVG(s.DANGEROUSOWNHALFLOSSES) as DANGEROUSOWNHALFLOSSES, AVG(s.ASSISTS) as ASSISTS
                FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE s
                JOIN {DB}.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
                LEFT JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                JOIN {DB}.WYSCOUT_SEASONS seas ON s.SEASON_WYID = seas.SEASON_WYID
                LEFT JOIN minut_beregning m_calc ON p.PLAYER_WYID = m_calc.PLAYER_WYID
                WHERE p.PLAYER_WYID NOT IN (SELECT PLAYER_WYID FROM hvidovre_spillere_2026)
                  AND seas.SEASONNAME = '{SOGT_SAESON}'
                  AND {liga_betingelse_stats}
                  {pos_betingelse}
                GROUP BY p.PLAYER_WYID, p.SHORTNAME, p.ROLE_NAME, t.OFFICIALNAME, p.CURRENTTEAM_WYID, m_calc.total_minutes_selected_liga
                HAVING COALESCE(m_calc.total_minutes_selected_liga, 0) >= 150
            )
            SELECT * FROM hvidovre_stats
            UNION ALL
            SELECT * FROM liga_stats
        """
        
        df = conn.query(sql_avanceret)
        
        if df is not None and not df.empty:
            df.columns = df.columns.str.lower()
            df['player_wyid'] = df['player_wyid'].astype(int)

            # Korriger navne og klub-tilhørsforhold for Hvidovre-spillere baseret på dit CSV-ark
            for idx, row in df.iterrows():
                wyid = row['player_wyid']
                # Hvis spilleren findes i dit CSV-ark, bruger vi navnet derfra for at fjerne mærkelige tegn
                csv_match = df_csv[df_csv['player_wyid'] == wyid]
                if not csv_match.empty:
                    df.at[idx, 'full_name'] = csv_match.iloc[0]['full_name']
                    # Hvis det er en Hvidovre-spiller, så sikrer vi klubnavnet
                    if row['is_active_hvidovre'] == 1:
                        df.at[idx, 'team_name'] = "Hvidovre IF"

            # Beregn live procenter og performance score
            df['pass_pct'] = (df['successfulpasses'] / df['passes'].replace(0, 1)) * 100

            config = POS_CONFIG[valgt_hovedkategori]
            score_col = 'pos_score'
            df[score_col] = 0.0
            for i, m_name in enumerate(config['metrics']):
                weight = config['weights'][i]
                val = df[m_name] if m_name in df.columns else 0
                df[score_col] += val * weight
            
            df[score_col] = df[score_col].round(1)

            df['dk_position'] = df['specific_position'].map(POS_TRANSLATIONS).fillna(df['specific_position'])
            df_sorteret = df.sort_values(score_col, ascending=False)
            
            # --- 4. SAML ENDELIGE TOPLISTE (Sikrer altid præcis 20 liga-spillere) ---
            liga_spillere = df_sorteret[df_sorteret['is_active_hvidovre'] == 0]
            hvidovre_spillere = df_sorteret[df_sorteret['is_active_hvidovre'] == 1]
            
            top_20_liga = liga_spillere.head(20)
            top_2_hvidovre = hvidovre_spillere.head(2)
            
            visnings_df = pd.concat([top_20_liga, top_2_hvidovre]).drop_duplicates(subset=['player_wyid'])
            
            if visnings_df.empty:
                st.info("Ingen spillere opfylder kriterierne for visning.")
                return
            
            visnings_df = visnings_df.sort_values(score_col, ascending=True)
            visnings_df['visningsnavn'] = visnings_df['full_name']

            farve_liste = [
                '#c11c2e' if row['is_active_hvidovre'] == 1 else '#1b365d'
                for _, row in visnings_df.iterrows()
            ]

            # --- 5. SPLIT-SCREEN VISNING ---
            rude_venstre, rude_hoejre = st.columns([1.1, 0.9])

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
                    xaxis={'title': f"{valgt_hovedkategori} Performance Score", 'showgrid': False},
                    showlegend=False, 
                    height=hoejde_graf,
                    margin=dict(l=10, r=10, t=10, b=10),
                    clickmode='event+select'
                )
                
                valgt_klik = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

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
                                Position (Fra systemet): <b>{valgt_spiller_data['dk_position']}</b><br>
                                Spillede minutter: <b>{int(valgt_spiller_data['total_minutes'])} min.</b><br>
                                Samlet Score ({valgt_hovedkategori}): <b>{valgt_spiller_data[score_col]}</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.write(f"**Underliggende P90-værdier ({valgt_hovedkategori}):**")
                    
                    for idx, m_name in enumerate(config['metrics']):
                        if m_name in valgt_spiller_data:
                            metric_vaerdi = valgt_spiller_data[m_name]
                            visnings_vaerdi = f"{metric_vaerdi:.1f}%" if "pct" in m_name else f"{metric_vaerdi:.2f}"
                        else:
                            visnings_vaerdi = "N/A"
                        
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
            st.info(f"Fandt ingen aktive stats eller minutter for de valgte turneringer.")

if __name__ == "__main__":
    vis_side()
