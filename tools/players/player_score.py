import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys
import os
import plotly.graph_objects as go

# Sikrer at Python kan finde data_load, selvom denne fil ligger i 'data'-mappen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.data_load import _get_snowflake_conn

def rens_specialtegn(val):
    """
    Oversætter ødelagte UTF-8/ANSI tegn (danske og baltiske/østlige tegn) 
    til deres rigtige bogstaver.
    """
    if not isinstance(val, str):
        return val

    tegn_map = {
        '√∏': 'ø', '√ò': 'Ø',
        '√¶': 'æ', '√Ü': 'Æ',
        '√•': 'å', '√Ö': 'Å',
        '√†': 'å',
        '√∫': 'ú',
        '≈°': 'š', '≈†': 'Š',
        '≈æ': 'ž', '≈Ω': 'Ž',
        '√≥': 'ó',
        '√©': 'é', '√®': 'è', '√¢': 'â', '√º': 'ü', '√∂': 'ö', '√§': 'ä'
    }

    for grimt, godt in tegn_map.items():
        val = val.replace(grimt, godt)

    return val

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
    if any(x in pos for x in ["angriber", "forward", "striker", "cf", "wf", "ss", "9'er", "fwd", "frontløber", "winger", "wing", "kant"]):
        return "Angriber"

    # MIDTBANESPILLER
    if any(x in pos for x in ["midtbane", "midfielder", "dmf", "cmf", "amf", "lm", "rm", "mid", "6'er", "8'er", "10'er"]):
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

    # De præcise, godkendte oversættelser
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
        "Forward": "Angriber",
        "Left Winger": "Venstre kant",
        "Right Winger": "Højre kant",
        "Goalkeeper": "Målmand",
        "Defender": "Forsvarsspiller",
        "Midfielder": "Midtbanespiller"
    }

    POS_CONFIG = {
        "Målmand": {
            "metrics": ["pass_pct", "clearances"],
            "weights": [5.0, 5.0],
            "labels": ["Pasnings %", "Clearinger"]
        },
        "Forsvarsspiller": {
            "metrics": ["interceptions", "defensiveduelswon", "clearances", "aerialduelswon", "pass_pct", "dangerousownhalflosses"],
            "weights": [4.0, 4.0, 3.5, 4.0, 2.5, -2.0], 
            "labels": ["Interceptions", "Vundne Def. Dueller", "Clearinger", "Vundne Luftdueller", "Pasnings %", "Farlige Boldtab (Egen banehalvdel)"]
        },
        "Midtbanespiller": {
            "metrics": ["pass_pct", "keypasses", "interceptions", "xgassist", "slidingtackles", "progressiverun"],
            "weights": [2.2, 4.5, 3.0, 4.0, 2.0, 1.5],
            "labels": ["Pasnings %", "Key Passes", "Interceptions", "xA", "Glidende Tacklinger", "Progressive løb"]
        },
        "Angriber": {
            "metrics": ["goals", "xg", "shots", "touchinbox", "dribbles", "assists"],
            "weights": [8.0, 2.0, 3.8, 3.4, 2.2, 6.0],
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

    df_csv = None
    for enc in ['utf-8-sig', 'latin-1', 'utf-8', 'cp1252']:
        try:
            df_csv = pd.read_csv(overskriv_sti, encoding=enc)
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

    # Rens og standardiser værdier
    df_csv['player_wyid'] = df_csv['player_wyid'].astype(int)
    df_csv['specific_position'] = df_csv['specific_position'].fillna("").astype(str).apply(rens_specialtegn)
    df_csv['full_name'] = df_csv['full_name'].fillna("").astype(str).apply(rens_specialtegn)
    df_csv['klub'] = df_csv['klub'].fillna("Ukendt Klub").astype(str).apply(rens_specialtegn).str.strip()

    df_csv['hovedkategori'] = df_csv['specific_position'].apply(map_til_hovedkategori)

    # --- 2. DYNAMISKE FILTRE ---
    col1, col2, col3 = st.columns(3)
    valgt_hovedkategori = col1.selectbox("Vælg Kategori", list(POS_CONFIG.keys()))

    df_csv_hoved = df_csv[df_csv['hovedkategori'] == valgt_hovedkategori]

    ekskluder_fra_dropdown = {
        "Målmand", "goalkeeper", "keeper", "gk",
        "Forsvarsspiller", "defender", "def",
        "Midtbanespiller", "midfielder", "mid",
        "Angriber", "forward", "striker", "fwd",
        "målmand", "goalkeeper", "keeper", "gk",
        "forsvarsspiller", "defender", "def",
        "midtbanespiller", "midfielder", "mid",
        "angriber", "forward", "striker", "fwd"
    }

    specifikke_muligheder = sorted([
        pos for pos in df_csv_hoved['specific_position'].dropna().unique().tolist()
        if pos.strip().lower() not in ekskluder_fra_dropdown and pos.strip() != ""
    ])

    visnings_positioner_map = {pos: POS_TRANSLATIONS.get(pos, pos) for pos in specifikke_muligheder}

    # Generer "Alle"-teksten
    if valgt_hovedkategori == "Målmand":
        alle_tekst = "Alle målmænd"
    elif valgt_hovedkategori == "Forsvarsspiller":
        alle_tekst = "Alle forsvarsspillere"
    elif valgt_hovedkategori == "Midtbanespiller":
        alle_tekst = "Alle midtbanespillere"
    elif valgt_hovedkategori == "Angriber":
        alle_tekst = "Alle angribere"
    else:
        alle_tekst = f"Alle {valgt_hovedkategori.lower()}e"

    valgt_specifik_visning = col2.selectbox(
        "Vælg Specifik Position", 
        [alle_tekst] + list(visnings_positioner_map.values())
    )

    faktisk_specifik_valg = None
    if valgt_specifik_visning != alle_tekst:
        for eng_pos, dk_pos in visnings_positioner_map.items():
            if dk_pos == valgt_specifik_visning:
                faktisk_specifik_valg = eng_pos
                break

    LIGA_VALGMULIGHEDER = {
        "alle": "Alle turneringer",
        335: "Superligaen",
        328: "Betinia Ligaen",
        329: "2. division",
        43319: "3. division",
    }
    valgt_liga_nøgle = col3.selectbox("Vælg Turnering", list(LIGA_VALGMULIGHEDER.keys()), format_func=lambda x: LIGA_VALGMULIGHEDER[x])

    # --- 3. FILTER LOGIK ---
    if faktisk_specifik_valg:
        target_wyids = df_csv_hoved[df_csv_hoved['specific_position'] == faktisk_specifik_valg]['player_wyid'].tolist()
    else:
        target_wyids = df_csv_hoved['player_wyid'].tolist()

    if not target_wyids:
        st.warning("Ingen spillere i din CSV-fil matcher de valgte filtre.")
        return

    sql_ids_str = f"({', '.join(map(str, target_wyids))})"

    # --- 4. SQL HENTNING ---
    if valgt_liga_nøgle == "alle":
        liga_betingelse_career = f"pc.COMPETITION_WYID IN {TILLADTE_LIGAER}"
        liga_betingelse_stats = f"s.COMPETITION_WYID IN {TILLADTE_LIGAER}"
    else:
        liga_betingelse_career = f"pc.COMPETITION_WYID = {valgt_liga_nøgle}"
        liga_betingelse_stats = f"s.COMPETITION_WYID = {valgt_liga_nøgle}"

    with st.spinner("Henter og beregner live-data..."):
        sql_avanceret = f"""
            WITH minut_kilde AS (
                SELECT 
                    pc.PLAYER_WYID,
                    SUM(CASE WHEN {liga_betingelse_career} THEN pc.MINUTESPLAYED ELSE 0 END) as total_minutes_selected_liga,
                    SUM(pc.MINUTESPLAYED) as total_minutes_all_ligas
                FROM {DB}.WYSCOUT_PLAYERCAREER pc
                JOIN {DB}.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
                WHERE s.SEASONNAME = '{SOGT_SAESON}'
                  AND pc.COMPETITION_WYID IN {TILLADTE_LIGAER}
                GROUP BY pc.PLAYER_WYID
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
                    COALESCE(t.OFFICIALNAME, 'Hvidovre IF') as TEAM_NAME,
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
                LEFT JOIN minut_kilde m_calc ON p.PLAYER_WYID = m_calc.PLAYER_WYID
                WHERE p.PLAYER_WYID IN {sql_ids_str}
                  AND p.PLAYER_WYID IN (SELECT PLAYER_WYID FROM hvidovre_spillere_2026)
                  AND seas.SEASONNAME = '{SOGT_SAESON}'
                  AND s.COMPETITION_WYID IN {TILLADTE_LIGAER}
                GROUP BY p.PLAYER_WYID, t.OFFICIALNAME, m_calc.total_minutes_all_ligas
                HAVING COALESCE(m_calc.total_minutes_all_ligas, 0) >= 150
            ),
            liga_stats AS (
                SELECT 
                    p.PLAYER_WYID,
                    COALESCE(t.OFFICIALNAME, 'Ukendt Klub') as TEAM_NAME,
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
                LEFT JOIN minut_kilde m_calc ON p.PLAYER_WYID = m_calc.PLAYER_WYID
                WHERE p.PLAYER_WYID IN {sql_ids_str}
                  AND p.PLAYER_WYID NOT IN (SELECT PLAYER_WYID FROM hvidovre_spillere_2026)
                  AND seas.SEASONNAME = '{SOGT_SAESON}'
                  AND {liga_betingelse_stats}
                GROUP BY p.PLAYER_WYID, t.OFFICIALNAME, m_calc.total_minutes_selected_liga
                HAVING COALESCE(m_calc.total_minutes_selected_liga, 0) >= 150
            )
            SELECT * FROM hvidovre_stats
            UNION ALL
            SELECT * FROM liga_stats
        """

        df_raw = conn.query(sql_avanceret)

    if df_raw is not None and not df_raw.empty:
        df_raw.columns = df_raw.columns.str.lower()
        df_raw['player_wyid'] = df_raw['player_wyid'].astype(int)

        # Drop potentielle overlap i kolonner inden merge, undtagen join-nøglen
        df_raw_clean = df_raw.drop(columns=[col for col in ['team_name'] if col in df_raw.columns and col in df_csv.columns])
        
        df = pd.merge(df_csv, df_raw_clean, on='player_wyid', how='inner')

        if df.empty:
            st.info(f"Ingen spillere i din CSV-fil matcher de valgte minut-kriterier i denne turnering.")
            return

        # --- REPARATION: TVING KLUB FRA CSV TIL AT GÆLDE OVERALT ---
        # 1. Sæt team_name udelukkende lig med 'klub' fra CSV-filen
        df['team_name'] = df['klub']
        
        # 2. Matcher alt der indeholder "hvidovre" (uanset stavemåde i CSV'en f.eks. "Hvidovre", "Hvidovre IF")
        df['is_active_hvidovre'] = np.where(
            df['klub'].str.strip().str.lower().str.contains("hvidovre", na=False), 
            1, 
            0
        )

        df['pass_pct'] = (df['successfulpasses'] / df['passes'].replace(0, 1)) * 100

        config = POS_CONFIG[valgt_hovedkategori]
        score_col = 'pos_score'
        df[score_col] = 0.0
        for i, m_name in enumerate(config['metrics']):
            weight = config['weights'][i]
            val = df[m_name] if m_name in df.columns else 0
            df[score_col] += val * weight

        df[score_col] = df[score_col].round(1)

        # Sikrer pæn dansk visning af både specifikke og brede positioner i spillerkortet
        df['dk_position'] = df['specific_position'].map(POS_TRANSLATIONS).fillna(df['specific_position'])
        df_sorteret = df.sort_values(score_col, ascending=False)

        # Filtrer nu udelukkende på den nyligt overskrevne CSV-status
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
            valgt_spiller_data = None

            # 1. FIND DEN VALGTE SPILLER
            if valgt_klik and "selection" in valgt_klik and valgt_klik["selection"]["points"]:
                klikket_navn = valgt_klik["selection"]["points"][0]["y"]
                matchende_spillere = df[df['full_name'] == klikket_navn]
                if not matchende_spillere.empty:
                    valgt_spiller_data = matchende_spillere.iloc[0]

            if valgt_spiller_data is None and not visnings_df.empty:
                # Default til nr. 1 på listen
                bedste_spiller_id = visnings_df.sort_values(score_col, ascending=False).iloc[0]['player_wyid']
                matchende_spillere = df[df['player_wyid'] == bedste_spiller_id]
                if not matchende_spillere.empty:
                    valgt_spiller_data = matchende_spillere.iloc[0]

            if valgt_spiller_data is not None:
                # --- INFO KORT ---
                st.markdown(f"""
                    <div class="score-card">
                        <div class="pos-title">{valgt_spiller_data['full_name']}</div>
                        <div style="font-size: 14px; color: #555; line-height: 1.5;">
                            Klub: <b>{valgt_spiller_data['team_name']}</b><br>
                            Position: <b>{valgt_spiller_data['dk_position']}</b><br>
                            Minutter: <b>{int(valgt_spiller_data['total_minutes'])} min.</b><br>
                            Score: <b>{valgt_spiller_data[score_col]}</b>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # --- RADAR CHART LOGIK ---
                metrics = config['metrics']
                labels = config['labels']
                
                # Beregn gennemsnit og spillerens værdier
                liga_avg = [df[m].mean() for m in metrics]
                spiller_vals = [valgt_spiller_data[m] for m in metrics]

                # Normalisering (0-100%)
                max_vals = [df[m].max() if df[m].max() != 0 else 1 for m in metrics]
                spiller_norm = [(v / m) * 100 for v, m in zip(spiller_vals, max_vals)]
                liga_norm = [(v / m) * 100 for v, m in zip(liga_avg, max_vals)]

                # Formatér værdier til visning på grafen
                val_text = [f"{v:.1f}%" if "pct" in metrics[i] else f"{v:.2f}" for i, v in enumerate(spiller_vals)]

                # Luk cirklen
                spiller_norm += [spiller_norm[0]]
                liga_norm += [liga_norm[0]]
                radar_labels = labels + [labels[0]]
                val_text += [val_text[0]]

                main_line_color = '#df003b' if valgt_spiller_data['is_active_hvidovre'] == 1 else '#1b365d'
                
                fig_radar = go.Figure()

                # 1. LIGA GENNEMSNIT
                fig_radar.add_trace(go.Scatterpolar(
                    r=liga_norm,
                    theta=radar_labels,
                    fill='toself',
                    name='Liga Gennemsnit',
                    line=dict(color='rgba(180, 180, 180, 0.4)', width=1),
                    fillcolor='rgba(200, 200, 200, 0.4)',
                    hoverinfo='skip'
                ))

                # 2. SPILLEREN (Rettet textfont struktur)
                fig_radar.add_trace(go.Scatterpolar(
                    r=spiller_norm,
                    theta=radar_labels,
                    mode='lines+markers+text',
                    text=val_text,
                    textposition="top center",
                    textfont=dict(
                        size=11, 
                        color=main_line_color, 
                        weight='bold'  # Placeret korrekt her
                    ),
                    fill=None,
                    name=valgt_spiller_data['full_name'],
                    line=dict(color=main_line_color, width=4),
                    marker=dict(size=8)
                ))

                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True, 
                            range=[0, 120], # Sat op til 120 for at sikre plads til labels/tal i toppen
                            showticklabels=False,
                            gridcolor='rgba(200, 200, 200, 0.2)'
                        ),
                        angularaxis=dict(
                            tickfont=dict(size=11, color="#333"),
                            rotation=90,
                            direction="clockwise"
                        ),
                        bgcolor='white'
                    ),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.15, # Lidt højere op
                        xanchor="center",
                        x=0.5
                    ),
                    height=600, # Øget højde for at undgå overlap
                    margin=dict(l=100, r=100, t=120, b=60) # Massive margins så intet klippes
                )

                st.plotly_chart(fig_radar, use_container_width=True)
                
                # --- LILLE TABEL MED RÅ DATA ---
                st.write("**Rå P90-værdier:**")
                cols = st.columns(len(metrics))
                for i, m in enumerate(metrics):
                    val = valgt_spiller_data[m]
                    vis_val = f"{val:.1f}%" if "pct" in m else f"{val:.2f}"
                    cols[i % 3].metric(labels[i], vis_val) # Fordeler over kolonner for at spare plads
            else:
                st.info("Vælg en spiller på grafen til venstre for at se detaljer.")
                
if __name__ == "__main__":
    vis_side()
