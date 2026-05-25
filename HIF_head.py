import streamlit as st
import pandas as pd
import datetime
import altair as alt
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn

# --- DIALOG-BOKS ---
@st.dialog("Alle Transfers", width="large")
def vis_transfer_dialog(df):
    if df.empty:
        st.write("Ingen data fundet.")
        return
    df_display = df.copy()
    df_display.columns = [str(c).upper().strip() for c in df_display.columns]
    df_display['TS_SORT'] = pd.to_datetime(df_display['TIMESTAMP'], errors='coerce')
    df_display = df_display.sort_values('TS_SORT', ascending=False)
    df_display['Dato'] = df_display['TS_SORT'].dt.strftime('%d/%m-%Y')
    pos_col = 'POSITION' if 'POSITION' in df_display.columns else 'POS'
    df_display['Spiller'] = df_display['NAVN'] + " (" + df_display.get(pos_col, '-').fillna('-') + ")"
    df_display['Skifte'] = df_display['SENESTE_KLUB'].fillna('?') + " ➔ " + df_display['KLUB'].fillna('?')
    
    def beregn_kontrakt(row):
        udloeb_raw = str(row.get('KONTRAKT_UDLOEB', '-'))
        if udloeb_raw == '-' or udloeb_raw == 'nan': return "-"
        try:
            udloeb_dt = pd.to_datetime(udloeb_raw, dayfirst=True, errors='coerce')
            if pd.notnull(udloeb_dt):
                aar = round((udloeb_dt - datetime.datetime.now()).days / 365.25)
                return f"{udloeb_raw} ({aar} år)"
            return udloeb_raw
        except: return udloeb_raw

    df_display['Kontrakt'] = df_display.apply(beregn_kontrakt, axis=1)
    st.dataframe(df_display[['Dato', 'Spiller', 'Skifte', 'Kontrakt', 'KILDE']],
                 column_config={"KILDE": st.column_config.LinkColumn("Kilde", display_text="Se kilde")},
                 hide_index=True, use_container_width=True)

def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            .stApp { background-color: #FFFFFF; }
            .card-title { color: #1a1a1a; font-size: 11px; font-weight: 700; margin-bottom: 12px; text-transform: uppercase; border-bottom: 1px solid #f0f0f0; padding-bottom: 6px; display: flex; justify-content: space-between; }
            .title-date { color: #888; font-weight: 500; text-transform: none; font-size: 11px; }
            .stats-table { width: 100%; font-size: 11px; border-collapse: collapse; table-layout: fixed; }
            .stats-label { color: #666; font-weight: 700; width: 50%; padding: 2px 0; }
            .stats-value { text-align: right; font-weight: 700; color: #111; padding: 2px 0; }
            .form-wrapper { display: flex; justify-content: space-between; gap: 4px; width: 100%; margin-top: 15px; padding-bottom: 10px; }
            .form-column { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; flex: 1; margin-bottom: 2px; }
            .res-pill { width: 100%; border-radius: 4px; color: white; text-align: center; font-size: 9px; font-weight: 800; padding: 3px 0; margin-bottom: 4px; }
            .legend-logo { width: 22px; height: 22px; object-fit: contain; }
            div.stButton > button { padding: 2px 8px !important; font-size: 10px !important; height: 26px !important; margin-top: 5px; }
            .list-item { font-size: 10px; margin-bottom: 6px; color: #333; display: grid; grid-template-columns: 1fr auto auto auto; align-items: center; gap: 4px; width: 100%; }
            .prev-club { color: #aaa; font-size: 9px; text-align: right; }
            .transfer-club { font-weight: 700; text-align: right; }
        </style>
    """, unsafe_allow_html=True)

def get_opta_queries(liga_f, saeson_f, hif_only=False):
    DB = "KLUB_HVIDOVREIF.AXIS"
    HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'
    tournament_map = {"NordicBet Liga": "dyjr458hcmrcy87fsabfsy87o", "Superliga": "29actv1ohj8r10kd9hu0jnb0n"}
    current_tournament_uuid = tournament_map.get(liga_f, "dyjr458hcmrcy87fsabfsy87o")
    match_id_subquery = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}'"
    hif_filter_matchinfo = f"AND (CONTESTANTHOME_OPTAUUID = '{HIF_UUID}' OR CONTESTANTAWAY_OPTAUUID = '{HIF_UUID}')" if hif_only else ""

    return {"opta_team_stats": f"""
        WITH MatchBase AS (
            SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS, CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE 
            FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}' {hif_filter_matchinfo}
        ),
        ExpectedGoalsPivot AS (
            SELECT MATCH_ID, CONTESTANT_OPTAUUID, 
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS XG, 
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) AS SHOTS, 
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) AS TOUCHES_IN_BOX 
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS WHERE MATCH_ID IN ({match_id_subquery}) GROUP BY 1, 2
        ),
        ForwardPassesPivot AS (
            SELECT MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, 
            COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 AND LEAD_X > (EVENT_X + 10) THEN 1 END) AS FORWARD_PASSES 
            FROM (SELECT MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, EVENT_TYPEID, EVENT_OUTCOME, EVENT_X, LEAD(EVENT_X) OVER (PARTITION BY MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as LEAD_X FROM {DB}.OPTA_EVENTS WHERE MATCH_OPTAUUID IN ({match_id_subquery}) AND EVENT_TYPEID = 1) 
            GROUP BY 1, 2
        ),
        MatchStatsPivot AS (
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, 
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION, 
            MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL END) AS TOTAL_PASSES, 
            MAX(CASE WHEN STAT_TYPE = 'wonCorners' THEN STAT_TOTAL END) AS CORNERS,
            MAX(CASE WHEN STAT_TYPE = 'totalCross' THEN STAT_TOTAL END) AS CROSSES,
            MAX(CASE WHEN STAT_TYPE = 'totalTackle' THEN STAT_TOTAL END) AS TACKLES, 
            MAX(FORMATIONUSED) AS FORMATION 
            FROM {DB}.OPTA_MATCHSTATS WHERE MATCH_OPTAUUID IN ({match_id_subquery}) GROUP BY 1, 2
        )
        SELECT b.*, 
        sh.XG AS HOME_XG, sh.SHOTS AS HOME_SHOTS, sh.TOUCHES_IN_BOX AS HOME_TOUCHES, 
        msh.POSSESSION AS HOME_POSS, msh.TOTAL_PASSES AS HOME_PASSES, msh.CORNERS AS HOME_CORNERS, msh.CROSSES AS HOME_CROSSES, msh.TACKLES AS HOME_TACKLES, msh.FORMATION AS HOME_FORMATION, 
        fp_h.FORWARD_PASSES AS HOME_FORWARD_PASSES, 
        sa.XG AS AWAY_XG, sa.SHOTS AS AWAY_SHOTS, sa.TOUCHES_IN_BOX AS AWAY_TOUCHES, 
        msa.POSSESSION AS AWAY_POSS, msa.TOTAL_PASSES AS AWAY_PASSES, msa.CORNERS AS AWAY_CORNERS, msa.CROSSES AS AWAY_CROSSES, msa.TACKLES AS AWAY_TACKLES, msa.FORMATION AS AWAY_FORMATION, 
        fp_a.FORWARD_PASSES AS AWAY_FORWARD_PASSES 
        FROM MatchBase b
        LEFT JOIN ExpectedGoalsPivot sh ON b.MATCH_OPTAUUID = sh.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = sh.CONTESTANT_OPTAUUID 
        LEFT JOIN ExpectedGoalsPivot sa ON b.MATCH_OPTAUUID = sa.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = sa.CONTESTANT_OPTAUUID 
        LEFT JOIN MatchStatsPivot msh ON b.MATCH_OPTAUUID = msh.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = msh.CONTESTANT_OPTAUUID 
        LEFT JOIN MatchStatsPivot msa ON b.MATCH_OPTAUUID = msa.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = msa.CONTESTANT_OPTAUUID 
        LEFT JOIN ForwardPassesPivot fp_h ON b.MATCH_OPTAUUID = fp_h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = fp_h.EVENT_CONTESTANT_OPTAUUID 
        LEFT JOIN ForwardPassesPivot fp_a ON b.MATCH_OPTAUUID = fp_a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = fp_a.EVENT_CONTESTANT_OPTAUUID 
        ORDER BY b.MATCH_DATE_FULL DESC"""}
    
def beregn_hold_stats(df_stats, team_uuid):
    played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    cols_to_numeric = ['TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'HOME_XG', 'AWAY_XG', 'HOME_POSS', 'AWAY_POSS']
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
    poss_all = pd.concat([home['HOME_POSS'], away['AWAY_POSS']]).dropna().mean()
    return {"gf": f"{gf / total_matches:.1f}", "ga": f"{ga / total_matches:.1f}", "xgf": f"{xgf / total_matches:.2f}", "xga": f"{xga / total_matches:.2f}", "poss": f"{int(round(poss_all))}%" if pd.notnull(poss_all) else "0%"}

def beregn_per_90(df_stats, team_uuid):
    played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    
    # Sørg for numeriske værdier
    cols = ['TOTAL_HOME_SCORE', 'HOME_XG', 'HOME_SHOTS', 'HOME_TOUCHES', 'HOME_PASSES', 'HOME_CORNERS', 'HOME_TACKLES',
            'TOTAL_AWAY_SCORE', 'AWAY_XG', 'AWAY_SHOTS', 'AWAY_TOUCHES', 'AWAY_PASSES', 'AWAY_CORNERS', 'AWAY_TACKLES']
    for col in cols:
        if col in played.columns:
            played[col] = pd.to_numeric(played[col], errors='coerce').fillna(0)

    hif_matches = played[((played['CONTESTANTHOME_OPTAUUID'].str.upper() == team_uuid.upper()) | 
                          (played['CONTESTANTAWAY_OPTAUUID'].str.upper() == team_uuid.upper()))].sort_values('MATCH_DATE_FULL')
    
    if len(hif_matches) == 0: return None

    # Hent seneste kamp data
    last_match = hif_matches.iloc[-1]
    is_home = str(last_match['CONTESTANTHOME_OPTAUUID']).upper() == team_uuid.upper()
    opp_name = last_match['CONTESTANTAWAY_NAME'] if is_home else last_match['CONTESTANTHOME_NAME']

    stats_map = {
        "Mål": ('TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE'),
        "xG": ('HOME_XG', 'AWAY_XG'),
        "Skud": ('HOME_SHOTS', 'AWAY_SHOTS'),
        "Touches": ('HOME_TOUCHES', 'AWAY_TOUCHES'),
        "Pasninger": ('HOME_PASSES', 'AWAY_PASSES'),
        "Hjørnespark": ('HOME_CORNERS', 'AWAY_CORNERS'),
        "Tacklinger": ('HOME_TACKLES', 'AWAY_TACKLES')
    }

    results = []
    for name, (h_col, a_col) in stats_map.items():
        hif_val = hif_matches.apply(lambda r: r[h_col] if str(r['CONTESTANTHOME_OPTAUUID']).upper() == team_uuid.upper() else r[a_col], axis=1).mean()
        liga_val = pd.concat([played[h_col], played[a_col]]).mean()
        last_val = last_match[h_col] if is_home else last_match[a_col]
        
        results.append({
            "Stat": name,
            "HIF": hif_val,
            "Liga": liga_val,
            "Diff": hif_val - liga_val,
            "Seneste": last_val,
            "Opponent": opp_name
        })
    
    return pd.DataFrame(results)

def beregn_kategori_indices(row, hif_uuid):
    is_home = str(row['CONTESTANTHOME_OPTAUUID']).upper() == hif_uuid.upper()
    
    # Hent værdier og sørg for at de er tal (konverter None/NaN til 0)
    xg = (row['HOME_XG'] if is_home else row['AWAY_XG'])
    shots = (row['HOME_SHOTS'] if is_home else row['AWAY_SHOTS'])
    touches = (row['HOME_TOUCHES'] if is_home else row['AWAY_TOUCHES'])
    
    # Defensiv data
    tackles = (row['HOME_TACKLES'] if is_home else row['AWAY_TACKLES'])
    goals_con = (row['TOTAL_AWAY_SCORE'] if is_home else row['TOTAL_HOME_SCORE'])
    
    # Standard situationer
    corners = (row['HOME_CORNERS'] if is_home else row['AWAY_CORNERS'])
    crosses = (row['HOME_CROSSES'] if is_home else row['AWAY_CROSSES'])
    opp_corners = (row['AWAY_CORNERS'] if is_home else row['HOME_CORNERS'])
    
    # --- FIX: Sørg for at alle værdier behandles som tal ved at bruge .fillna(0) ---
    # Vi bruger en lokal funktion til at sikre tal-format
    def v(val):
        try:
            return float(val) if pd.notnull(val) else 0.0
        except:
            return 0.0

    # Beregninger med sikker konvertering
    off_idx = (v(xg) * 1.5) + (v(shots) * 0.3) + (v(touches) * 0.05)
    def_idx = -(float(goals_con) * 2.0) + (float(tackles) * 0.2)
    off_std = (v(corners) * 0.5) + (v(crosses) * 0.2)
    def_std = -(v(opp_corners) * 0.3)
    
    return pd.Series({'Offensiv': off_idx, 'Defensiv': def_idx, 'Off_Std': off_std, 'Def_Std': def_std})
def get_team_name(uuid, home_name, away_name, is_home):
    # Opret map fra din TEAMS dictionary
    uuid_to_name = {str(v.get('opta_uuid')).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    # Prøv at finde navnet via UUID
    name = uuid_to_name.get(str(uuid).strip().upper())
    if name:
        return name
    
    # Fallback: Brug navnet direkte fra databasen, hvis UUID ikke er mappet
    return home_name if not is_home else away_name
    
def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return
    DB, LIGA_UUID, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "dyjr458hcmrcy87fsabfsy87o", "8GXD9RY2580PU1B1DD5NY9YMY"
    queries = get_opta_queries("NordicBet Liga", "2025/2026", hif_only=False)
    df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_stats = conn.query(queries["opta_team_stats"])
    df_stats.columns = [str(c).upper() for c in df_stats.columns]
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        with st.container(border=True):
            hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID.strip().upper()) | (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == HIF_UUID.strip().upper())]
            today = pd.Timestamp.today().normalize()
            future = hif_m[hif_m['MATCH_DATE_FULL'] >= today].sort_values('MATCH_DATE_FULL')
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['CONTESTANTAWAY_OPTAUUID'] if str(nk['CONTESTANTHOME_OPTAUUID']).upper() == HIF_UUID.strip().upper() else nk['CONTESTANTHOME_OPTAUUID']
                opp_name = opta_to_name.get(str(opp_id).upper(), "Ukendt")
                st.markdown(f"<div class='card-title'><span>NÆSTE KAMP vs. {opp_name.upper()}</span><span class='title-date'>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</span></div>", unsafe_allow_html=True)
                hif_stats = beregn_hold_stats(df_stats, HIF_UUID)
                opp_stats = beregn_hold_stats(df_stats, opp_id)
                hif_logo = TEAMS.get("Hvidovre", {}).get("logo", "")
                opp_logo = TEAMS.get(opp_name, {}).get("logo", "")
                stats_html = f"""<table class='stats-table' style='width: 100%;'><tr><td style='width: 34%;'></td><td style='text-align: center; width: 33%; border-bottom: 1px solid #eee; padding-bottom: 4px;'><img src='{hif_logo}' style='width: 22px; height: 22px; object-fit: contain;'></td><td style='text-align: center; width: 33%; border-bottom: 1px solid #eee; padding-bottom: 4px;'><img src='{opp_logo}' style='width: 22px; height: 22px; object-fit: contain;'></td></tr><tr><td class='stats-label' style='text-align: left;'>Possession</td><td class='stats-value' style='text-align: center;'>{hif_stats['poss']}</td><td class='stats-value' style='text-align: center;'>{opp_stats['poss']}</td></tr><tr><td class='stats-label' style='text-align: left;'>Mål for/imod</td><td class='stats-value' style='text-align: center;'>{hif_stats['gf']}/{hif_stats['ga']}</td><td class='stats-value' style='text-align: center;'>{opp_stats['gf']}/{opp_stats['ga']}</td></tr><tr><td class='stats-label' style='text-align: left;'>xG for/imod</td><td class='stats-value' style='text-align: center;'>{hif_stats['xgf']}/{hif_stats['xga']}</td><td class='stats-value' style='text-align: center;'>{opp_stats['xgf']}/{opp_stats['xga']}</td></tr></table>"""
                st.markdown(stats_html, unsafe_allow_html=True)
                opp_m = df_matches[((df_matches['CONTESTANTHOME_OPTAUUID'] == opp_id) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == opp_id)) & (df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
                if not opp_m.empty:
                    f_items = ""
                    for _, m in opp_m.iloc[::-1].iterrows():
                        is_h = str(m['CONTESTANTHOME_OPTAUUID']).upper() == str(opp_id).upper()
                        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                        res_col = "#28a745" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else ("#6c757d" if h_s == a_s else "#dc3545")
                        o_uuid = m['CONTESTANTAWAY_OPTAUUID'] if is_h else m['CONTESTANTHOME_OPTAUUID']
                        o_logo = TEAMS.get(opta_to_name.get(str(o_uuid).upper(), ""), {}).get("logo", "")
                        f_items += f"<div class='form-column'><div class='res-pill' style='background:{res_col};'>{h_s}-{a_s}</div><img src='{o_logo}' class='legend-logo'></div>"
                    st.markdown(f"<div class='form-wrapper'>{f_items}</div>", unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>TRANSFERS</span></div>', unsafe_allow_html=True)
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv")
                df_t['TS_DATE'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
                df_t = df_t.dropna(subset=['TS_DATE'])
                for _, r in df_t.sort_values('TS_DATE', ascending=False).head(7).iterrows():
                    st.markdown(f"<div class='list-item'><span>{r['TS_DATE'].strftime('%d/%m')}: <b>{r['NAVN']}</b></span><span class='prev-club'>{r.get('SENESTE_KLUB', '?')}</span><span class='transfer-club'>➔ {r.get('KLUB', '?')}</span></div>", unsafe_allow_html=True)
                if st.button("Se alle transfers", key="transfers_btn", use_container_width=True): vis_transfer_dialog(df_t)
            except: st.caption("Kunne ikke indlæse transfer-data")

    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>SCOUTING</span></div>', unsafe_allow_html=True)

# Række 2: Sæson Snit (Venstre) + Trendlines (Højre)
    main_col, trend_area = st.columns([1, 2])
    
    with main_col:
        with st.container(border=True): # Start container
            st.markdown('<div class="card-title"><span>HVIDOVRE IF vs. LIGA</span></div>', unsafe_allow_html=True)
            df_stats_comp = beregn_per_90(df_stats, HIF_UUID)
            
            # Sørg for at alt dette er indrykket under 'with'
            if df_stats_comp is not None:
                opp_navn = df_stats_comp.iloc[0]['Opponent']
                opp_header = f"vs. {opp_navn}"
                
                html = f"""<table class='stats-table'>
                    <thead><tr>
                        <th>Stat</th>
                        <th style='text-align:right;'>{opp_header}</th>
                        <th>HIF</th>
                        <th>Liga</th>
                        <th>Diff</th>
                    </tr></thead>"""
                    
                for _, r in df_stats_comp.iterrows():
                    diff_color = "#28a745" if r['Diff'] > 0 else "#dc3545"
                    html += f"""<tr>
                        <td class='stats-label'>{r['Stat']}</td>
                        <td class='stats-value' style='text-align:right; color:#1a1a1a;'>{r['Seneste']:.0f}</td>
                        <td class='stats-value'>{r['HIF']:.2f}</td>
                        <td class='stats-value'>{r['Liga']:.2f}</td>
                        <td class='stats-value' style='color:{diff_color}; font-weight:800;'>{r['Diff']:+.2f}</td>
                    </tr>"""
                html += "</table>"
                st.markdown(html, unsafe_allow_html=True)
            
    with trend_area:
        # 1. Hent og forbered data
        hif_recent = df_stats[
            ((df_stats['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID.strip().upper()) | 
             (df_stats['CONTESTANTAWAY_OPTAUUID'].str.upper() == HIF_UUID.strip().upper())) & 
            (df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))
        ].sort_values('MATCH_DATE_FULL', ascending=True).copy()

        if not hif_recent.empty:
            num_cols = ['HOME_XG', 'AWAY_XG', 'HOME_SHOTS', 'AWAY_SHOTS', 'HOME_TOUCHES', 'AWAY_TOUCHES', 
                        'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'HOME_CORNERS', 'AWAY_CORNERS', 'HOME_TACKLES', 'AWAY_TACKLES']
            for col in num_cols:
                hif_recent[col] = pd.to_numeric(hif_recent[col], errors='coerce').fillna(0)

            # --- KORREKT HENTNING AF NAVNE VIA TEAMS ORDBOGEN ---
            # Vi laver en map fra UUID til Navn baseret på din TEAMS dictionary
            uuid_to_name = {str(v.get('opta_uuid')).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
            
            hif_recent['OPPONENT_NAME'] = hif_recent.apply(
                lambda r: get_team_name(
                    # Hvis vi er hjemme, så tag away_uuid, ellers tag home_uuid
                    r['CONTESTANTAWAY_OPTAUUID'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == HIF_UUID.strip().upper() 
                    else r['CONTESTANTHOME_OPTAUUID'],
                    # Send navnene med som fallback
                    r['CONTESTANTHOME_NAME'],
                    r['CONTESTANTAWAY_NAME'],
                    # Er vi hjemme?
                    str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == HIF_UUID.strip().upper()
                ), axis=1
            )
            
            hif_recent['HOME_OR_AWAY'] = hif_recent.apply(lambda r: "H" if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == HIF_UUID.strip().upper() else "U", axis=1)

            # Beregn indices
            indices = hif_recent.apply(lambda row: beregn_kategori_indices(row, HIF_UUID), axis=1)
            hif_recent = pd.concat([hif_recent, indices], axis=1)
            hif_recent['index'] = range(1, len(hif_recent) + 1)

            # Liga-snit (samme som før)
            played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
            for col in num_cols: played[col] = pd.to_numeric(played[col], errors='coerce').fillna(0)
            liga_indices = played.apply(lambda row: beregn_kategori_indices(row, "DUMMY_UUID"), axis=1)
            liga_means = liga_indices.mean()

            # 3. Layout og Grafer
            r1_c1, r1_c2 = st.columns(2)
            r2_c1, r2_c2 = st.columns(2)
            
            categories = [
                ("OFFENSIV", "Offensiv", "xG, Skud, Touches", r1_c1), 
                ("DEFENSIV", "Defensiv", "Mål imod, tacklinger", r2_c1), 
                ("OFF. STD", "Off_Std", "Hjørnespark", r1_c2), 
                ("DEF. STD", "Def_Std", "Hjørnespark", r2_c2)
            ]

            for title, col, desc, target in categories:
                with target:
                    st.markdown(f"<div style='font-weight:700; font-size:14px; margin-bottom:0px;'>{title}</div>", unsafe_allow_html=True)
                    st.caption(f"<div style='margin-top:-5px;'>{desc}</div>", unsafe_allow_html=True)
                    
                    hif_avg = hif_recent[col].mean()
                    
                    # Tooltip header: vs. Esbjerg 2-2 (H)
                    hif_recent['tooltip_header'] = hif_recent.apply(
                        lambda r: f"vs. {r['OPPONENT_NAME']} {int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])} ({r['HOME_OR_AWAY']})", axis=1
                    )
                    hif_recent['diff_label'] = hif_recent[col].apply(lambda x: f"{x - hif_avg:+.1f}")
                    
                    line = alt.Chart(hif_recent).mark_line(
                        color='#AAAAAA', 
                        point=alt.MarkConfig(color='#C41E3A', filled=True)
                    ).encode(
                        x=alt.X('index:O', axis=None),
                        y=alt.Y(f'{col}:Q', axis=None, scale=alt.Scale(zero=False)),
                        tooltip=[
                            alt.Tooltip('tooltip_header', title='Kamp'),
                            alt.Tooltip(f'{col}', title='Score', format='.1f'),
                            alt.Tooltip('diff_label', title='Diff vs Snit')
                        ]
                    ).properties(height=120)

                    hif_rule = alt.Chart(pd.DataFrame({'y': [hif_avg]})).mark_rule(color='#C41E3A', strokeDash=[3,3]).encode(y='y:Q')
                    liga_rule = alt.Chart(pd.DataFrame({'y': [liga_means[col]]})).mark_rule(color='#000000', strokeDash=[2,2], opacity=0.4).encode(y='y:Q')
                    
                    st.altair_chart(line + hif_rule + liga_rule, use_container_width=True)
                
if __name__ == "__main__":
    vis_side()
