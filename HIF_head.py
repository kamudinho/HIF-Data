import streamlit as st
import pandas as pd
import altair as alt

from data.utils.team_mapping import (
    SEASONS,
    COMPETITIONS,
    SEASON_LEAGUE_MAPPER,
    TEAMS,
    COMPETITION_NAME as DEFAULT_COMP,
    TOURNAMENTCALENDAR_NAME as DEFAULT_SEASON
)
from data.data_load import _get_snowflake_conn
from data.utils.stattype_map import STAT_TYPE_MAP

def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            .stApp { background-color: #FFFFFF; }
            
            /* Sørg for at kolonnerne strækker sig ens */
            [data-testid="stHorizontalBlock"] {
                display: flex;
                align-items: stretch;
            }
            [data-testid="stHorizontalBlock"] > div {
                display: flex;
                flex-direction: column;
                flex: 1;
            }
            [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {
                height: 100% !important;
                display: flex;
                flex-direction: column;
                flex: 1;
            }
            [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlockBorderWrapper"] > div {
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlockBorderWrapper"] > div > div {
                flex: 1;
                display: flex;
                flex-direction: column;
            }

            /* Fast højde på boksen, men start indholdet fra toppen (flex-start) */
            .fixed-card-content {
                height: 380px !important;
                max-height: 380px !important;
                display: flex;
                flex-direction: column;
                justify-content: flex-start !important;
                overflow: hidden;
            }
            
            /* Fjern unødvendig afstand i Streamlit's interne elementer */
            [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
                gap: 0rem !important;
            }

            .stats-table { width: 100%; font-size: 11px; border-collapse: collapse; table-layout: auto; }
            .stats-table th { text-align: center; padding: 4px; color: #888; font-weight: 600; white-space: nowrap; }
            .stats-label { text-align: left !important; color: #666; font-weight: 700; width: 40%; padding: 4px 8px 4px 0; }
            .stats-value { text-align: center !important; font-weight: 700; color: #111; padding: 4px 4px; min-width: 30px; }
            .card-title { color: #1a1a1a; font-size: 11px; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; border-bottom: 1px solid #f0f0f0; padding-bottom: 6px; display: flex; justify-content: space-between; }
            
            /* Stilling-tabel styling */
            .table-standings { width: 100%; font-size: 11px; border-collapse: collapse; }
            .table-standings th { text-align: center; padding: 4px 2px; color: #888; border-bottom: 1px solid #eee; font-weight: 600; }
            .table-standings td { padding: 4px 2px; text-align: center; color: #333; font-weight: 600; }
            .table-standings .team-cell { text-align: left; font-weight: 700; color: #111; }
            .table-standings .hif-row { background-color: #ffebe8; }
        </style>
    """, unsafe_allow_html=True)

def resolve_team_name(uuid_str, raw_name=""):
    """Sikker opslag af holdnavn uanset casing og sprogvariationer."""
    if not uuid_str:
        return raw_name
    uuid_clean = str(uuid_str).strip().upper()
    
    for t_name, t_info in TEAMS.items():
        if str(t_info.get('opta_uuid', '')).strip().upper() == uuid_clean:
            return t_name
            
    if raw_name:
        clean_raw = raw_name.replace("FF", "").replace("IF", "").strip()
        for t_name in TEAMS.keys():
            if clean_raw.lower() in t_name.lower() or t_name.lower() in clean_raw.lower():
                return t_name
        return raw_name
        
    return "Ukendt"

def get_opta_queries(calendar_uuid, hif_uuid):
    DB = "KLUB_HVIDOVREIF.AXIS"
    calendar_filter = f"WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'" if calendar_uuid else ""

    return {"opta_team_stats": f"""
        WITH CombinedStats AS (
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, STAT_TYPE, TRY_CAST(STAT_TOTAL AS FLOAT) AS STAT_VALUE
            FROM {DB}.OPTA_MATCHSTATS
            UNION ALL
            SELECT MATCH_ID, CONTESTANT_OPTAUUID, STAT_TYPE, TRY_CAST(STAT_VALUE AS FLOAT)
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        ),
        MatchBase AS (
            SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS, CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE 
            FROM {DB}.OPTA_MATCHINFO {calendar_filter}
        ),
        PivotStats AS (
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS XG,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) AS SHOTS,
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) AS TOUCHES_IN_BOX,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_VALUE END) AS POSSESSION,
            SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_VALUE ELSE 0 END) AS PASSES,
            SUM(CASE WHEN STAT_TYPE = 'wonCorners' THEN STAT_VALUE ELSE 0 END) AS CORNERS,
            SUM(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN STAT_VALUE ELSE 0 END) AS OFF_TARGET,
            SUM(CASE WHEN STAT_TYPE = 'totalThrows' THEN STAT_VALUE ELSE 0 END) AS THROWS,
            SUM(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN STAT_VALUE ELSE 0 END) AS FREEKICKS,
            SUM(CASE WHEN STAT_TYPE = 'totalTackle' THEN STAT_VALUE ELSE 0 END) AS TACKLES,
            SUM(CASE WHEN STAT_TYPE = 'totalClearance' THEN STAT_VALUE ELSE 0 END) AS CLEARANCES
            FROM CombinedStats
            GROUP BY 1, 2
        )
        SELECT b.*, 
        s1.XG AS HOME_XG, s1.SHOTS AS HOME_SHOTS, s1.TOUCHES_IN_BOX AS HOME_TOUCHES, s1.POSSESSION AS HOME_POSSESSION, s1.PASSES AS HOME_PASSES, s1.CORNERS AS HOME_CORNERS, s1.OFF_TARGET AS HOME_OFF_TARGET, s1.THROWS AS HOME_THROWS, s1.FREEKICKS AS HOME_FREEKICKS, s1.TACKLES AS HOME_TACKLES, s1.CLEARANCES AS HOME_CLEARANCES,
        s2.XG AS AWAY_XG, s2.SHOTS AS AWAY_SHOTS, s2.TOUCHES_IN_BOX AS AWAY_TOUCHES, s2.POSSESSION AS AWAY_POSSESSION, s2.PASSES AS AWAY_PASSES, s2.CORNERS AS AWAY_CORNERS, s2.OFF_TARGET AS AWAY_OFF_TARGET, s2.THROWS AS AWAY_THROWS, s2.FREEKICKS AS AWAY_FREEKICKS, s2.TACKLES AS AWAY_TACKLES, s2.CLEARANCES AS AWAY_CLEARANCES
        FROM MatchBase b
        LEFT JOIN PivotStats s1 ON b.MATCH_OPTAUUID = s1.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = s1.CONTESTANT_OPTAUUID
        LEFT JOIN PivotStats s2 ON b.MATCH_OPTAUUID = s2.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = s2.CONTESTANT_OPTAUUID
        ORDER BY b.MATCH_DATE_FULL DESC"""}

def beregn_kategori_indices(row, hif_uuid):
    is_home = str(row['CONTESTANTHOME_OPTAUUID']).strip().upper() == hif_uuid.strip().upper()
    def get_val(col_h, col_a):
        val = row[col_h] if is_home else row[col_a]
        return float(val) if pd.notnull(val) else 0.0
    
    xg, shots, touches = get_val('HOME_XG', 'AWAY_XG'), get_val('HOME_SHOTS', 'AWAY_SHOTS'), get_val('HOME_TOUCHES', 'AWAY_TOUCHES')
    tackles, goals_con = get_val('HOME_TACKLES', 'AWAY_TACKLES'), get_val('TOTAL_AWAY_SCORE', 'TOTAL_HOME_SCORE')
    corners, opp_corners = get_val('HOME_CORNERS', 'AWAY_CORNERS'), get_val('AWAY_CORNERS', 'HOME_CORNERS')
    
    off_idx = (xg * 1.5) + (shots * 0.3) + (touches * 0.05)
    def_idx = -(goals_con * 2.0) + (tackles * 0.2)
    off_std = (corners * 0.5) 
    def_std = -(opp_corners * 0.3)
    return pd.Series({'Offensiv': off_idx, 'Defensiv': def_idx, 'Off_Std': off_std, 'Def_Std': def_std})

def beregn_per_90(df_stats, team_uuid):
    played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    if played.empty: return None

    numeric_cols = ['TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'HOME_XG', 'AWAY_XG', 'HOME_POSSESSION', 'AWAY_POSSESSION', 'HOME_OFF_TARGET', 'AWAY_OFF_TARGET', 'HOME_THROWS', 'AWAY_THROWS', 'HOME_FREEKICKS', 'AWAY_FREEKICKS', 'HOME_CORNERS', 'AWAY_CORNERS', 'HOME_TACKLES', 'AWAY_TACKLES', 'HOME_CLEARANCES', 'AWAY_CLEARANCES', 'HOME_PASSES', 'AWAY_PASSES']
    for col in numeric_cols:
        if col in played.columns:
            played[col] = pd.to_numeric(played[col], errors='coerce').fillna(0)

    hif_matches = played[((played['CONTESTANTHOME_OPTAUUID'].str.upper() == team_uuid.upper()) | (played['CONTESTANTAWAY_OPTAUUID'].str.upper() == team_uuid.upper()))].sort_values('MATCH_DATE_FULL')
    if len(hif_matches) == 0: return None

    last_match = hif_matches.iloc[-1]
    is_home = str(last_match['CONTESTANTHOME_OPTAUUID']).strip().upper() == team_uuid.strip().upper()
    opp_uuid = last_match['CONTESTANTAWAY_OPTAUUID'] if is_home else last_match['CONTESTANTHOME_OPTAUUID']
    opp_raw = last_match['CONTESTANTAWAY_NAME'] if is_home else last_match['CONTESTANTHOME_NAME']
    opp_name = resolve_team_name(opp_uuid, opp_raw)

    stats_map = {
        STAT_TYPE_MAP["possessionPercentage"]: ('HOME_POSSESSION', 'AWAY_POSSESSION'),
        STAT_TYPE_MAP["totalPass"]: ('HOME_PASSES', 'AWAY_PASSES'),
        STAT_TYPE_MAP["shotOffTarget"]: ('HOME_OFF_TARGET', 'AWAY_OFF_TARGET'),
        STAT_TYPE_MAP["goals"]: ('TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE'),
        STAT_TYPE_MAP["expectedGoals"]: ('HOME_XG', 'AWAY_XG'),
        STAT_TYPE_MAP["totalTackle"]: ('HOME_TACKLES', 'AWAY_TACKLES'),
        STAT_TYPE_MAP["totalClearance"]: ('HOME_CLEARANCES', 'AWAY_CLEARANCES'),
        STAT_TYPE_MAP["wonCorners"]: ('HOME_CORNERS', 'AWAY_CORNERS'),
        STAT_TYPE_MAP["totalThrows"]: ('HOME_THROWS', 'AWAY_THROWS'),
        STAT_TYPE_MAP["fkFoulLost"]: ('HOME_FREEKICKS', 'AWAY_FREEKICKS')
    }
    results = []
    for display_name, (h_col, a_col) in stats_map.items():
        hif_val = hif_matches.apply(lambda r: r[h_col] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == team_uuid.strip().upper() else r[a_col], axis=1).mean()
        liga_val = pd.concat([played[h_col], played[a_col]]).mean()
        last_val = last_match[h_col] if is_home else last_match[a_col]
        results.append({"Stat": display_name, "HIF": hif_val, "Liga": liga_val, "Diff": hif_val - liga_val, "Seneste": last_val, "Opponent": opp_name})
    return pd.DataFrame(results)

def beregn_hold_stats(df_stats, team_uuid):
    played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    cols_to_numeric = ['TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'HOME_XG', 'AWAY_XG', 'HOME_POSSESSION', 'AWAY_POSSESSION']
    for col in cols_to_numeric:
        if col in played.columns: played[col] = pd.to_numeric(played[col], errors='coerce')
    home = played[played['CONTESTANTHOME_OPTAUUID'].str.upper() == team_uuid.upper()]
    away = played[played['CONTESTANTAWAY_OPTAUUID'].str.upper() == team_uuid.upper()]
    total_matches = len(home) + len(away)
    if total_matches == 0: return {"gf": "0.0", "ga": "0.0", "xgf": "0.0", "xga": "0.0", "poss": "0%"}
    gf = home['TOTAL_HOME_SCORE'].sum() + away['TOTAL_AWAY_SCORE'].sum()
    ga = home['TOTAL_AWAY_SCORE'].sum() + away['TOTAL_HOME_SCORE'].sum()
    xgf = home['HOME_XG'].fillna(0).sum() + away['AWAY_XG'].fillna(0).sum()
    xga = home['AWAY_XG'].fillna(0).sum() + away['HOME_XG'].fillna(0).sum()
    poss_all = pd.concat([home['HOME_POSSESSION'], away['AWAY_POSSESSION']]).dropna().mean()
    return {"gf": f"{gf / total_matches:.1f}", "ga": f"{ga / total_matches:.1f}", "xgf": f"{xgf / total_matches:.2f}", "xga": f"{xga / total_matches:.2f}", "poss": f"{int(round(poss_all))}%" if pd.notnull(poss_all) else "0%"}

def beregn_stilling(df_matches, valgt_saeson, valgt_turnering):
    stats = {}
    saesons_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, [])
    if not saesons_hold:
        saesons_hold = sorted(TEAMS.keys())

    for name in saesons_hold:
        stats[name] = {'K': 0, 'V': 0, 'U': 0, 'T': 0, 'MF': 0, 'P': 0}

    if df_matches is not None and not df_matches.empty and 'MATCH_STATUS' in df_matches.columns:
        played = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
        for _, row in played.iterrows():
            h_uuid = str(row['CONTESTANTHOME_OPTAUUID']).upper()
            a_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).upper()
            
            h_name = resolve_team_name(h_uuid, row.get('CONTESTANTHOME_NAME', ''))
            a_name = resolve_team_name(a_uuid, row.get('CONTESTANTAWAY_NAME', ''))
            
            if h_name not in stats: stats[h_name] = {'K': 0, 'V': 0, 'U': 0, 'T': 0, 'MF': 0, 'P': 0}
            if a_name not in stats: stats[a_name] = {'K': 0, 'V': 0, 'U': 0, 'T': 0, 'MF': 0, 'P': 0}

            try:
                h_g = int(row['TOTAL_HOME_SCORE'])
                a_g = int(row['TOTAL_AWAY_SCORE'])
            except:
                continue

            stats[h_name]['K'] += 1
            stats[a_name]['K'] += 1
            stats[h_name]['MF'] += (h_g - a_g)
            stats[a_name]['MF'] += (a_g - h_g)

            if h_g > a_g:
                stats[h_name]['V'] += 1; stats[h_name]['P'] += 3; stats[a_name]['T'] += 1
            elif a_g > h_g:
                stats[a_name]['V'] += 1; stats[a_name]['P'] += 3; stats[h_name]['T'] += 1
            else:
                stats[h_name]['U'] += 1; stats[a_name]['U'] += 1
                stats[h_name]['P'] += 1; stats[a_name]['P'] += 1

    df_standings = pd.DataFrame.from_dict(stats, orient='index').reset_index()
    df_standings.columns = ['Hold', 'K', 'V', 'U', 'T', 'MF', 'P']
    df_standings = df_standings.sort_values(by=['P', 'MF', 'Hold'], ascending=[False, False, True]).reset_index(drop=True)
    df_standings.index = df_standings.index + 1
    return df_standings

def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return
    
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = TEAMS.get("Hvidovre", {}).get("opta_uuid", "8gxd9ry2580pu1b1dd5ny9ymy").upper()
    
    active_season = DEFAULT_SEASON
    active_comp = DEFAULT_COMP
    calendar_uuid = SEASONS.get(active_season, {}).get(active_comp)

    # 1. Hent kampprogram
    df_matches = pd.DataFrame()
    if calendar_uuid:
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'")
        df_matches.columns = [str(c).upper() for c in df_matches.columns]
        if 'MATCH_DATE_FULL' in df_matches.columns:
            df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)

    # 2. Hent stats
    queries = get_opta_queries(calendar_uuid, HIF_UUID)
    df_stats = conn.query(queries["opta_team_stats"])
    df_stats.columns = [str(c).upper() for c in df_stats.columns]

    if df_stats.empty or len(df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]) == 0:
        fallback_queries = get_opta_queries(None, HIF_UUID)
        df_stats = conn.query(fallback_queries["opta_team_stats"])
        df_stats.columns = [str(c).upper() for c in df_stats.columns]

    # --- TOPSEKTION: 3 KOLONNER (FAST BOKS-HØJDE MED INDHOLD STARTENDE ØVERST) ---
    col1, col2, col3 = st.columns([1, 1, 1])

    # KOLONNE 1: NÆSTE MODSTANDER
    with col1:
        with st.container(border=True):
            st.markdown("""
                <div class='fixed-card-content'>
                    <div class='card-title'><span>NÆSTE MODSTANDER</span></div>
            """, unsafe_allow_html=True)
            
            future = pd.DataFrame()
            if not df_matches.empty:
                hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID) | 
                                   (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == HIF_UUID)]
                today = pd.Timestamp.today().normalize()
                future = hif_m[hif_m['MATCH_DATE_FULL'] >= today].sort_values('MATCH_DATE_FULL')

            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['CONTESTANTAWAY_OPTAUUID'] if str(nk['CONTESTANTHOME_OPTAUUID']).upper() == HIF_UUID else nk['CONTESTANTHOME_OPTAUUID']
                opp_raw = nk['CONTESTANTAWAY_NAME'] if str(nk['CONTESTANTHOME_OPTAUUID']).upper() == HIF_UUID else nk['CONTESTANTHOME_NAME']
                opp_name = resolve_team_name(opp_id, opp_raw)
                
                st.markdown(f"<div class='card-title' style='border:none; margin-top:0px; padding-bottom:0; font-size: 13px;'><span>vs. {opp_name.upper()}</span><span>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</span></div>", unsafe_allow_html=True)
                
                hif_stats = beregn_hold_stats(df_stats, HIF_UUID)
                opp_stats = beregn_hold_stats(df_stats, opp_id)
                hif_logo = TEAMS.get("Hvidovre", {}).get("logo", "")
                opp_logo = TEAMS.get(opp_name, {}).get("logo", "")
                
                stats_html = f"""
                <table class='stats-table' style='width: 100%; margin-top: 4px;'>
                    <tr><td style='width: 34%;'></td>
                        <td style='text-align: center; width: 33%; border-bottom: 1px solid #eee; padding-bottom: 4px;'><img src='{hif_logo}' style='width: 22px; height: 22px; object-fit: contain;'></td>
                        <td style='text-align: center; width: 33%; border-bottom: 1px solid #eee; padding-bottom: 4px;'><img src='{opp_logo}' style='width: 22px; height: 22px; object-fit: contain;'></td>
                    </tr>
                    <tr><td class='stats-label'>Possession</td><td class='stats-value'>{hif_stats['poss']}</td><td class='stats-value'>{opp_stats['poss']}</td></tr>
                    <tr><td class='stats-label'>Mål for/imod</td><td class='stats-value'>{hif_stats['gf']}/{hif_stats['ga']}</td><td class='stats-value'>{opp_stats['gf']}/{opp_stats['ga']}</td></tr>
                    <tr><td class='stats-label'>xG for/imod</td><td class='stats-value'>{hif_stats['xgf']}/{hif_stats['xga']}</td><td class='stats-value'>{opp_stats['xgf']}/{opp_stats['xga']}</td></tr>
                </table>"""
                st.markdown(stats_html, unsafe_allow_html=True)
            else:
                st.caption(f"Afventer næste kamp for sæson {active_season}")
                
            st.markdown("</div>", unsafe_allow_html=True)

    # KOLONNE 2: HVIDOVRE IF vs. LIGA
    with col2:
        with st.container(border=True):
            st.markdown("""
                <div class='fixed-card-content'>
                    <div class='card-title'><span>HVIDOVRE IF vs. LIGA</span></div>
            """, unsafe_allow_html=True)
            
            df_stats_comp = beregn_per_90(df_stats, HIF_UUID)
            if df_stats_comp is not None:
                opp_navn = df_stats_comp.iloc[0]['Opponent']
                opp_header = f"vs. {opp_navn}"
                html = f"<table class='stats-table'><thead><tr><th></th><th>{opp_header}</th><th>HIF</th><th>Liga</th><th>Diff</th></tr></thead><tbody>"
                for _, r in df_stats_comp.iterrows():
                    diff_color = "#28a745" if r['Diff'] > 0 else "#dc3545"
                    html += f"<tr><td class='stats-label'>{r['Stat']}</td><td class='stats-value'>{r['Seneste']:.0f}</td><td class='stats-value'>{r['HIF']:.2f}</td><td class='stats-value'>{r['Liga']:.2f}</td><td class='stats-value' style='color:{diff_color}; font-weight:800;'>{r['Diff']:+.2f}</td></tr>"
                html += "</tbody></table>"
                st.markdown(html, unsafe_allow_html=True)
                
            st.markdown("</div>", unsafe_allow_html=True)

    # KOLONNE 3: STILLING
    with col3:
        with st.container(border=True):
            st.markdown(f"""
                <div class='fixed-card-content'>
                    <div class='card-title'><span>STILLING ({active_comp.upper()})</span></div>
            """, unsafe_allow_html=True)
            
            df_stilling = beregn_stilling(df_matches, active_season, active_comp)
            if not df_stilling.empty:
                table_html = "<table class='table-standings'><thead><tr><th>#</th><th style='text-align:left;'>Hold</th><th>K</th><th>MF</th><th>P</th></tr></thead><tbody>"
                for idx, row in df_stilling.head(12).iterrows():
                    row_class = "hif-row" if "Hvidovre" in row['Hold'] else ""
                    mf_sign = f"+{row['MF']}" if row['MF'] > 0 else str(row['MF'])
                    table_html += f"<tr class='{row_class}'><td>{idx}</td><td class='team-cell'>{row['Hold']}</td><td>{row['K']}</td><td>{mf_sign}</td><td><b>{row['P']}</b></td></tr>"
                table_html += "</tbody></table>"
                st.markdown(table_html, unsafe_allow_html=True)
            else:
                st.caption("Ingen stillingsdata fundet.")
                
            st.markdown("</div>", unsafe_allow_html=True)

    # --- BUNDSEKTION: TRENDGRAFER ---
    with st.container(border=True):
        st.markdown('<div class="card-title"><span>PRESTATIONS-TRENDS</span></div>', unsafe_allow_html=True)
        hif_recent = df_stats[((df_stats['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID) | (df_stats['CONTESTANTAWAY_OPTAUUID'].str.upper() == HIF_UUID)) & (df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=True).tail(10).copy()
        
        if not hif_recent.empty:
            num_cols = ['HOME_XG', 'AWAY_XG', 'HOME_SHOTS', 'AWAY_SHOTS', 'HOME_TOUCHES', 'AWAY_TOUCHES', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'HOME_CORNERS', 'AWAY_CORNERS', 'HOME_TACKLES', 'AWAY_TACKLES']
            for col in num_cols: 
                hif_recent[col] = pd.to_numeric(hif_recent[col], errors='coerce').fillna(0)
            
            hif_recent['OPPONENT_NAME'] = hif_recent.apply(lambda r: resolve_team_name(r['CONTESTANTAWAY_OPTAUUID'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == HIF_UUID else r['CONTESTANTHOME_OPTAUUID'], r['CONTESTANTAWAY_NAME'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == HIF_UUID else r['CONTESTANTHOME_NAME']), axis=1)
            hif_recent['HOME_OR_AWAY'] = hif_recent.apply(lambda r: "H" if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == HIF_UUID else "U", axis=1)
            
            indices = hif_recent.apply(lambda row: beregn_kategori_indices(row, HIF_UUID), axis=1)
            hif_recent = pd.concat([hif_recent, indices], axis=1)
            hif_recent['index'] = range(1, len(hif_recent) + 1)
            
            played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
            for col in num_cols: 
                played[col] = pd.to_numeric(played[col], errors='coerce').fillna(0)
            
            liga_indices = played.apply(lambda row: beregn_kategori_indices(row, "DUMMY_UUID"), axis=1)
            liga_means = liga_indices.mean()
            
            r1_c1, r1_c2, r2_c1, r2_c2 = st.columns(4)
            categories = [
                ("OFFENSIV", "Offensiv", "xG, Skud, Touches", r1_c1), 
                ("DEFENSIV", "Defensiv", "Mål imod, tacklinger", r1_c2), 
                ("OFF. STD", "Off_Std", "Hjørnespark", r2_c1), 
                ("DEF. STD", "Def_Std", "Hjørnespark", r2_c2)
            ]
            
            for title, col, desc, target in categories:
                with target:
                    st.markdown(f"<div style='font-weight:700; font-size:12px; margin-bottom:0px;'>{title}</div>", unsafe_allow_html=True)
                    st.caption(f"<div style='margin-top:-5px; font-size:10px;'>{desc}</div>", unsafe_allow_html=True)
                    hif_avg = hif_recent[col].mean()
                    hif_recent['tooltip_header'] = hif_recent.apply(lambda r: f"vs. {r['OPPONENT_NAME']} {int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])} ({r['HOME_OR_AWAY']})", axis=1)
                    hif_recent['diff_label'] = hif_recent[col].apply(lambda x: f"{x - hif_avg:+.1f}")
                    
                    line = alt.Chart(hif_recent).mark_line(color='#AAAAAA', point=alt.MarkConfig(color='#C41E3A', filled=True)).encode(
                        x=alt.X('index:O', axis=None), 
                        y=alt.Y(f'{col}:Q', axis=None, scale=alt.Scale(zero=False)), 
                        tooltip=[alt.Tooltip('tooltip_header', title='Kamp'), alt.Tooltip(f'{col}', title='Score', format='.1f'), alt.Tooltip('diff_label', title='Diff vs Snit')]
                    ).properties(height=120)
                    
                    st.altair_chart(line + alt.Chart(pd.DataFrame({'y': [hif_avg]})).mark_rule(color='#C41E3A', strokeDash=[3,3]).encode(y='y:Q') + alt.Chart(pd.DataFrame({'y': [liga_means[col]]})).mark_rule(color='#000000', strokeDash=[2,2], opacity=0.4).encode(y='y:Q'), use_container_width=True)

if __name__ == "__main__":
    vis_side()
