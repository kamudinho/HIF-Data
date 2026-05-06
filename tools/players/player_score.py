import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys
import os

# Sikrer at Python kan finde data_load, selvom denne fil ligger i 'data'-mappen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.data_load import _get_snowflake_conn

def rens_specialtegn(val):
    if not isinstance(val, str):
        return val
    tegn_map = {
        '√∏': 'ø', '√ò': 'Ø', '√¶': 'æ', '√Ü': 'Æ', '√•': 'å', '√Ö': 'Å',
        '√†': 'å', '√∫': 'ú', '≈°': 'š', '≈†': 'Š', '≈æ': 'ž', '≈Ω': 'Ž',
        '√≥': 'ó', '√©': 'é', '√®': 'è', '√¢': 'â', '√º': 'ü', '√∂': 'ö', '√§': 'ä'
    }
    for grimt, godt in tegn_map.items():
        val = val.replace(grimt, godt)
    return val

def map_til_hovedkategori(position_str):
    if not isinstance(position_str, str):
        return "Ukendt"
    pos = position_str.strip().lower()
    if any(x in pos for x in ["målmand", "goalkeeper", "keeper", "gk"]):
        return "Målmand"
    if any(x in pos for x in ["forsvar", "defender", "cb", "lb", "rb", "lwb", "rwb", "stopper", "back", "def"]):
        return "Forsvarsspiller"
    if any(x in pos for x in ["angriber", "forward", "striker", "cf", "wf", "ss", "9'er", "fwd", "frontløber", "winger", "wing", "kant"]):
        return "Angriber"
    if any(x in pos for x in ["midtbane", "midfielder", "dmf", "cmf", "amf", "lm", "rm", "mid", "6'er", "8'er", "10'er"]):
        return "Midtbanespiller"
    return "Ukendt"

def vis_side():
    st.markdown("""
        <style>
        .score-card { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #df003b; margin-bottom: 15px; }
        .pos-title { font-size: 22px; font-weight: bold; color: #1E1E1E; margin-bottom: 2px; }
        .metric-row { 
            display: flex; justify-content: space-between; align-items: center; 
            padding: 10px 15px; background-color: #ffffff; border: 1px solid #e0e0e0; 
            border-radius: 6px; margin-bottom: 8px; 
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
        "Center Back": "Midterforsvarer", "Left Back": "Venstre Back", "Right Back": "Højre Back",
        "Left Wing Back": "Venstre Wingback", "Right Wing Back": "Højre Wingback",
        "Defensive Midfielder": "Defensiv Midtbane", "Central Midfielder": "Central Midtbane",
        "Attacking Midfielder": "Offensiv Midtbane", "Left Midfielder": "Venstre Midtbane",
        "Right Midfielder": "Højre Midtbane", "Forward": "Angriber", "Left Winger": "Venstre kant",
        "Right Winger": "Højre kant", "Goalkeeper": "Målmand", "Defender": "Forsvarsspiller",
        "Midfielder": "Midtbanespiller"
    }

    POS_CONFIG = {
        "Målmand": {
            "metrics": ["pass_pct", "clearances"],
            "weights": [5.0, 5.0],
            "labels": ["Pasnings %", "Clearinger"]
        },
        "Forsvarsspiller": {
            "metrics": ["interceptions", "defensiveduelswon", "clearances", "aerialduels", "pass_pct", "dangerousownhalflosses"],
            "weights": [5.0, 4.0, 3.5, 4.0, 2.5, -3.0], 
            "labels": ["Interceptions", "Vundne Def. Dueller", "Clearinger", "Vundne Luftdueller", "Pasnings %", "Farlige Boldtab (Egen banehalvdel)"]
        },
        "Midtbanespiller": {
            "metrics": ["pass_pct", "keypasses", "interceptions", "xgassist", "slidingtackles", "progressiverun"],
            "weights": [8.0, 4.5, 3.0, 4.0, 2.0, 1.5],
            "labels": ["Pasnings %", "Key Passes", "Interceptions", "xA", "Glidende Tacklinger", "Progressive løb"]
        },
        "Angriber": {
            "metrics": ["goals", "xg", "shots", "touchinbox", "dribbles", "assists"],
            "weights": [6.0, 4.0, 3.8, 2.4, 1.2, 2.0],
            "labels": ["Mål", "xG", "Skud", "Berøringer i felt", "Driblinger", "Assists"]
        }
    }

    # --- 1. INDLÆS CSV-FIL ---
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

    try:
        df_csv = pd.read_csv(overskriv_sti, encoding='utf-8-sig')
    except Exception:
        df_csv = pd.read_csv(overskriv_sti, encoding='latin-1')

    if df_csv.empty:
        st.error("Kunne ikke indlæse CSV-filen korrekt.")
        return

    df_csv.columns = df_csv.columns.str.lower().str.strip()
    df_csv = df_csv.rename(columns={'navn': 'full_name', 'position': 'specific_position'})
    
    df_csv['player_wyid'] = df_csv['player_wyid'].astype(int)
    df_csv['specific_position'] = df_csv['specific_position'].fillna("").astype(str).apply(rens_specialtegn)
    df_csv['full_name'] = df_csv['full_name'].fillna("").astype(str).apply(rens_specialtegn)
    df_csv['klub'] = df_csv['klub'].fillna("").astype(str).apply(rens_specialtegn)
    df_csv['hovedkategori'] = df_csv['specific_position'].apply(map_til_hovedkategori)

    # --- 2. DYNAMISKE FILTRE ---
    col1, col2, col3 = st.columns(3)
    valgt_hovedkategori = col1.selectbox("Vælg Kategori", list(POS_CONFIG.keys()), key="cat_select")
    
    df_csv_hoved = df_csv[df_csv['hovedkategori'] == valgt_hovedkategori]
    
    specifikke_muligheder = sorted([
        pos for pos in df_csv_hoved['specific_position'].dropna().unique().tolist()
        if pos.strip().lower() not in {"målmand", "goalkeeper", "keeper", "gk", "forsvarsspiller", "defender", "def", "midtbanespiller", "midfielder", "mid", "angriber", "forward", "striker", "fwd"} and pos.strip() != ""
    ])
    
    visnings_positioner_map = {pos: POS_TRANSLATIONS.get(pos, pos) for pos in specifikke_muligheder}
    alle_tekst = f"Alle {valgt_hovedkategori.lower()}e" if valgt_hovedkategori != "Målmand" else "Alle målmænd"
    
    valgt_specifik_visning = col2.selectbox("Vælg Specifik Position", [alle_tekst] + list(visnings_positioner_map.values()), key="spec_pos_select")
    
    faktisk_specifik_valg = next((eng for eng, dk in visnings_positioner_map.items() if dk == valgt_specifik_visning), None)

    LIGA_VALGMULIGHEDER = {
        "alle": "Alle turneringer", 328: "NordicBet Liga", 335: "Superliga",
        329: "2. division", 43319: "3. division"
    }
    valgt_liga_nøgle = col3.selectbox("Vælg Turnering", list(LIGA_VALGMULIGHEDER.keys()), format_func=lambda x: LIGA_VALGMULIGHEDER[x], key="liga_select")

    # --- 3. FILTER LOGIK ---
    # Vi henter ALTID alle spillere fra CSV'en for hovedkategorien ned fra Snowflake, 
    # så vi kan filtrere dem dynamisk i Python (både Hvidovre- og liga-spillere)
    alle_wyids_i_kategori = df_csv_hoved['player_wyid'].tolist()

    if not alle_wyids_i_kategori:
        st.warning("Ingen spillere matcher de valgte filtre.")
        return

    sql_ids_str = f"({', '.join(map(str, alle_wyids_i_kategori))})"

    # --- 4. DUAL SQL QUERY (HVIDOVRE VS LIGA) ---
    # Hvidovre-spillere læses på tværs af alle tilladte ligaer (så de altid kommer med uanset dit filter)
    # Liga-spillere læses KUN for den valgte turnering i dropdownen
    liga_betingelse_stats = f"s.COMPETITION_WYID IN {TILLADTE_LIGAER}" if valgt_liga_nøgle == "alle" else f"s.COMPETITION_WYID = {valgt_liga_nøgle}"

    with st.spinner("Henter og beregner live-data..."):
        sql_samlet = f"""
            WITH minut_kilde AS (
                SELECT 
                    pc.PLAYER_WYID,
                    MAX(CASE WHEN pc.TEAM_WYID = {HVIDOVRE_TEAM_WYID} THEN 1 ELSE 0 END) as is_active_hvidovre,
                    -- Minutter for den specifikke valgte liga (til eksterne spillere)
                    SUM(CASE WHEN pc.COMPETITION_WYID = {valgt_liga_nøgle if valgt_liga_nøgle != 'alle' else 'pc.COMPETITION_WYID'} THEN pc.MINUTESPLAYED ELSE 0 END) as total_minutes_selected_liga,
                    -- Minutter i alt for Hvidovre-spillere
                    SUM(pc.MINUTESPLAYED) as total_minutes_all_ligas
                FROM {DB}.WYSCOUT_PLAYERCAREER pc
                JOIN {DB}.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
                WHERE s.SEASONNAME = '{SOGT_SAESON}'
                  AND pc.COMPETITION_WYID IN {TILLADTE_LIGAER}
                GROUP BY pc.PLAYER_WYID
            ),
            hvidovre_pulje AS (
                SELECT 
                    p.PLAYER_WYID,
                    COALESCE(m_calc.total_minutes_all_ligas, 0) as total_minutes,
                    1 as is_active_hvidovre,
                    AVG(s.GOALS) as GOALS, AVG(s.XGSHOT) AS XG, AVG(s.SHOTS) as SHOTS,
                    AVG(s.TOUCHINBOX) as TOUCHINBOX, AVG(s.DRIBBLES) as DRIBBLES,
                    AVG(s.PASSES) as PASSES, AVG(s.SUCCESSFULPASSES) as SUCCESSFULPASSES,
                    AVG(s.KEYPASSES) as KEYPASSES, AVG(s.INTERCEPTIONS) as INTERCEPTIONS,
                    AVG(s.XGASSIST) as XGASSIST, AVG(s.SLIDINGTACKLES) as SLIDINGTACKLES,
                    AVG(s.PROGRESSIVERUN) as PROGRESSIVERUN, AVG(s.DEFENSIVEDUELSWON) as DEFENSIVEDUELSWON,
                    AVG(s.CLEARANCES) as CLEARANCES, AVG(s.AERIALDUELS) AS AERIALDUELS,
                    AVG(s.DANGEROUSOWNHALFLOSSES) as DANGEROUSOWNHALFLOSSES, AVG(s.ASSISTS) as ASSISTS
                FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE s
                JOIN {DB}.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
                JOIN {DB}.WYSCOUT_SEASONS seas ON s.SEASON_WYID = seas.SEASON_WYID
                JOIN minut_kilde m_calc ON p.PLAYER_WYID = m_calc.PLAYER_WYID
                WHERE p.PLAYER_WYID IN {sql_ids_str}
                  AND m_calc.is_active_hvidovre = 1
                  AND seas.SEASONNAME = '{SOGT_SAESON}'
                  AND s.COMPETITION_WYID IN {TILLADTE_LIGAER} -- Hvidovre data hentes altid på tværs af tilladte ligaer
                GROUP BY p.PLAYER_WYID, m_calc.total_minutes_all_ligas
                HAVING COALESCE(m_calc.total_minutes_all_ligas, 0) >= 150
            ),
            liga_pulje AS (
                SELECT 
                    p.PLAYER_WYID,
                    COALESCE(m_calc.total_minutes_selected_liga, 0) as total_minutes,
                    0 as is_active_hvidovre,
                    AVG(s.GOALS) as GOALS, AVG(s.XGSHOT) AS XG, AVG(s.SHOTS) as SHOTS,
                    AVG(s.TOUCHINBOX) as TOUCHINBOX, AVG(s.DRIBBLES) as DRIBBLES,
                    AVG(s.PASSES) as PASSES, AVG(s.SUCCESSFULPASSES) as SUCCESSFULPASSES,
                    AVG(s.KEYPASSES) as KEYPASSES, AVG(s.INTERCEPTIONS) as INTERCEPTIONS,
                    AVG(s.XGASSIST) as XGASSIST, AVG(s.SLIDINGTACKLES) as SLIDINGTACKLES,
                    AVG(s.PROGRESSIVERUN) as PROGRESSIVERUN, AVG(s.DEFENSIVEDUELSWON) as DEFENSIVEDUELSWON,
                    AVG(s.CLEARANCES) as CLEARANCES, AVG(s.AERIALDUELS) AS AERIALDUELS,
                    AVG(s.DANGEROUSOWNHALFLOSSES) as DANGEROUSOWNHALFLOSSES, AVG(s.ASSISTS) as ASSISTS
                FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_AVERAGE s
                JOIN {DB}.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID
                JOIN {DB}.WYSCOUT_SEASONS seas ON s.SEASON_WYID = seas.SEASON_WYID
                JOIN minut_kilde m_calc ON p.PLAYER_WYID = m_calc.PLAYER_WYID
                WHERE p.PLAYER_WYID IN {sql_ids_str}
                  AND m_calc.is_active_hvidovre = 0
                  AND seas.SEASONNAME = '{SOGT_SAESON}'
                  AND {liga_betingelse_stats} -- Eksterne spillere filtreres på den valgte turnering
                GROUP BY p.PLAYER_WYID, m_calc.total_minutes_selected_liga
                HAVING COALESCE(m_calc.total_minutes_selected_liga, 0) >= 150
            )
            SELECT * FROM hvidovre_pulje
            UNION ALL
            SELECT * FROM liga_pulje
        """
        
        df_raw = conn.query(sql_samlet)
        
        if df_raw is not None and not df_raw.empty:
            df_raw.columns = df_raw.columns.str.lower()
            df_raw['player_wyid'] = df_raw['player_wyid'].astype(int)

            df = pd.merge(df_csv, df_raw, on='player_wyid', how='inner')

            if df.empty:
                st.info("Ingen spillere matcher spilletidskriterierne (min. 150 min.) i denne turnering.")
                return

            # Sætter klubnavnet dynamisk baseret på is_active_hvidovre-status
            df['team_name'] = np.where(df['is_active_hvidovre'] == 1, "Hvidovre IF", df['klub'])
            df['pass_pct'] = (df['successfulpasses'] / df['passes'].replace(0, 1)) * 100

            # --- PERFORMANCE SCORE BEREGNING ---
            config = POS_CONFIG[valgt_hovedkategori]
            score_col = 'pos_score'
            df[score_col] = 0.0
            for i, m_name in enumerate(config['metrics']):
                weight = config['weights'][i]
                df[score_col] += (df[m_name] if m_name in df.columns else 0) * weight
            
            df[score_col] = df[score_col].round(1)
            df['dk_position'] = df['specific_position'].map(POS_TRANSLATIONS).fillna(df['specific_position'])

            # --- DYNAMISK FILTRERING PÅ SPECIFIK POSITION ---
            # Vi filtrerer datarammen her, så både Hvidovre- og eksterne spillere følger det valgte positionsfilter!
            if faktisk_specifik_valg:
                df_filtreret = df[df['specific_position'] == faktisk_specifik_valg]
            else:
                df_filtreret = df

            if df_filtreret.empty:
                st.warning("Ingen spillere matcher den valgte specifikke position.")
                return

            df_sorteret = df_filtreret.sort_values(score_col, ascending=False)
            
            # Opdel i Hvidovre og Liga for at lave top 20 + top 2 reglen
            hvidovre_spillere = df_sorteret[df_sorteret['is_active_hvidovre'] == 1]
            liga_spillere = df_sorteret[df_sorteret['is_active_hvidovre'] == 0]
            
            # Nu tager vi de 20 bedste liga-spillere og fletter dem med de 2 bedste Hvidovre-spillere på den valgte position
            visnings_df = pd.concat([liga_spillere.head(20), hvidovre_spillere.head(2)]).drop_duplicates(subset=['player_wyid'])
            
            # Sorter til grafen (stigende, så den højeste score lander øverst i Plotly horisontal bar)
            visnings_df = visnings_df.sort_values(score_col, ascending=True)
            visnings_df['visningsnavn'] = visnings_df['full_name']

            farve_liste = ['#c11c2e' if active == 1 else '#1b365d' for active in visnings_df['is_active_hvidovre']]

            rude_venstre, rude_hoejre = st.columns([1.1, 0.9])

            with rude_venstre:
                st.subheader("Performance Scoreboard")
                hoejde_graf = max(500, len(visnings_df) * 26)
                
                fig = px.bar(
                    visnings_df, x=score_col, y='visningsnavn', orientation='h',
                    text=score_col, template='plotly_white', custom_data=['player_wyid']
                )
                fig.update_traces(
                    marker_color=farve_liste, textposition='inside',   
                    textfont=dict(color='white', size=11, family="Arial"), 
                    insidetextanchor='end', cliponaxis=False
                )
                fig.update_layout(
                    yaxis={'categoryorder':'total ascending', 'title': None}, 
                    xaxis={'title': f"{valgt_hovedkategori} Performance Score", 'showgrid': False},
                    showlegend=False, height=hoejde_graf, margin=dict(l=10, r=10, t=10, b=10),
                    clickmode='event+select'
                )
                valgt_klik = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

            with rude_hoejre:
                valgt_spiller_data = None
                if valgt_klik and "selection" in valgt_klik and valgt_klik["selection"]["points"]:
                    klikket_wyid = valgt_klik["selection"]["points"][0]["customdata"][0]
                    valgt_spiller_data = df_filtreret[df_filtreret['player_wyid'] == klikket_wyid].iloc[0]
                elif not visnings_df.empty:
                    # Default til den bedste spiller overhovedet på listen
                    bedste_spiller_id = visnings_df.sort_values(score_col, ascending=False).iloc[0]['player_wyid']
                    valgt_spiller_data = df_filtreret[df_filtreret['player_wyid'] == bedste_spiller_id].iloc[0]

                if valgt_spiller_data is not None:
                    st.markdown(f"""
                        <div class="score-card">
                            <div class="pos-title">{valgt_spiller_data['full_name']}</div>
                            <div style="font-size: 14px; color: #555; line-height: 1.5;">
                                Klub: <b>{valgt_spiller_data['team_name']}</b><br>
                                Position: <b>{valgt_spiller_data['dk_position']}</b><br>
                                Minutter: <b>{int(valgt_spiller_data['total_minutes'])} min.</b><br>
                                Samlet score ({valgt_hovedkategori}): <b>{valgt_spiller_data[score_col]}</b>
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
            st.info("Fandt ingen aktive stats eller minutter for de valgte spillere i turneringerne.")

if __name__ == "__main__":
    vis_side()
