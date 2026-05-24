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
    
    # 1. Dato-formatering
    df_display['TS_SORT'] = pd.to_datetime(df_display['TIMESTAMP'], errors='coerce')
    df_display = df_display.sort_values('TS_SORT', ascending=False)
    df_display['Dato'] = df_display['TS_SORT'].dt.strftime('%d/%m-%Y')
    
    # 2. Spiller
    pos_col = 'POSITION' if 'POSITION' in df_display.columns else 'POS'
    df_display['Spiller'] = df_display['NAVN'] + " (" + df_display.get(pos_col, '-').fillna('-') + ")"
    
    # 3. Skifte
    df_display['Skifte'] = df_display['SENESTE_KLUB'].fillna('?') + " ➔ " + df_display['KLUB'].fillna('?')
    
    # 4. Kontrakt-logik
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
            .stats-table { width: 100%; font-size: 10px; border-collapse: collapse; table-layout: fixed; }
            .stats-label { color: #666; font-weight: 700; width: 45%; padding: 2px 0; }
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
        WITH MatchBase AS (SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS, CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{current_tournament_uuid}' {hif_filter_matchinfo}),
        ExpectedGoalsPivot AS (SELECT MATCH_ID, CONTESTANT_OPTAUUID, SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS XG, SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_VALUE ELSE 0 END) AS SHOTS, SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) AS TOUCHES_IN_BOX FROM {DB}.OPTA_MATCHEXPECTEDGOALS WHERE MATCH_ID IN ({match_id_subquery}) GROUP BY 1, 2),
        ForwardPassesPivot AS (SELECT MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 AND LEAD_X > (EVENT_X + 10) THEN 1 END) AS FORWARD_PASSES FROM (SELECT MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, EVENT_TYPEID, EVENT_OUTCOME, EVENT_X, LEAD(EVENT_X) OVER (PARTITION BY MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as LEAD_X FROM {DB}.OPTA_EVENTS WHERE MATCH_OPTAUUID IN ({match_id_subquery}) AND EVENT_TYPEID = 1) GROUP BY 1, 2),
        MatchStatsPivot AS (SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION, MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL END) AS TOTAL_PASSES, MAX(CASE WHEN STAT_TYPE = 'totalYellowCard' THEN STAT_TOTAL END) AS YELLOW_CARDS, MAX(FORMATIONUSED) AS FORMATION FROM {DB}.OPTA_MATCHSTATS WHERE MATCH_OPTAUUID IN ({match_id_subquery}) GROUP BY 1, 2)
        SELECT b.*, sh.XG AS HOME_XG, sh.SHOTS AS HOME_SHOTS, sh.TOUCHES_IN_BOX AS HOME_TOUCHES, msh.POSSESSION AS HOME_POSS, msh.TOTAL_PASSES AS HOME_PASSES, msh.FORMATION AS HOME_FORMATION, fp_h.FORWARD_PASSES AS HOME_FORWARD_PASSES, sa.XG AS AWAY_XG, sa.SHOTS AS AWAY_SHOTS, sa.TOUCHES_IN_BOX AS AWAY_TOUCHES, msa.POSSESSION AS AWAY_POSS, msa.TOTAL_PASSES AS AWAY_PASSES, msa.FORMATION AS AWAY_FORMATION, fp_a.FORWARD_PASSES AS AWAY_FORWARD_PASSES FROM MatchBase b LEFT JOIN ExpectedGoalsPivot sh ON b.MATCH_OPTAUUID = sh.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = sh.CONTESTANT_OPTAUUID LEFT JOIN ExpectedGoalsPivot sa ON b.MATCH_OPTAUUID = sa.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = sa.CONTESTANT_OPTAUUID LEFT JOIN MatchStatsPivot msh ON b.MATCH_OPTAUUID = msh.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = msh.CONTESTANT_OPTAUUID LEFT JOIN MatchStatsPivot msa ON b.MATCH_OPTAUUID = msa.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = msa.CONTESTANT_OPTAUUID LEFT JOIN ForwardPassesPivot fp_h ON b.MATCH_OPTAUUID = fp_h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = fp_h.EVENT_CONTESTANT_OPTAUUID LEFT JOIN ForwardPassesPivot fp_a ON b.MATCH_OPTAUUID = fp_a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = fp_a.EVENT_CONTESTANT_OPTAUUID ORDER BY b.MATCH_DATE_FULL DESC"""}

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

def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return
    
    # Data hentning
    DB, LIGA_UUID, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "dyjr458hcmrcy87fsabfsy87o", "8GXD9RY2580PU1B1DD5NY9YMY"
    queries = get_opta_queries("NordicBet Liga", "2025/2026", hif_only=False)
    df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_stats = conn.query(queries["opta_team_stats"])
    df_stats.columns = [str(c).upper() for c in df_stats.columns]
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)

    # --- 1. ØVERSTE SEKTION (Eksisterende) ---
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
                stats_html = f"""<table class='stats-table'><tr><td></td><td><img src='{hif_logo}' style='width:22px;'></td><td><img src='{opp_logo}' style='width:22px;'></td></tr>
                <tr><td class='stats-label'>Possession</td><td class='stats-value'>{hif_stats['poss']}</td><td class='stats-value'>{opp_stats['poss']}</td></tr>
                <tr><td class='stats-label'>Mål for/imod</td><td class='stats-value'>{hif_stats['gf']}/{hif_stats['ga']}</td><td class='stats-value'>{opp_stats['gf']}/{opp_stats['ga']}</td></tr>
                <tr><td class='stats-label'>xG for/imod</td><td class='stats-value'>{hif_stats['xgf']}/{hif_stats['xga']}</td><td class='stats-value'>{opp_stats['xgf']}/{opp_stats['xga']}</td></tr></table>"""
                st.markdown(stats_html, unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>TRANSFERS</span></div>', unsafe_allow_html=True)
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv")
                df_t['TS_DATE'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
                for _, r in df_t.sort_values('TS_DATE', ascending=False).head(7).iterrows():
                    st.markdown(f"<div class='list-item'><span>{r['TS_DATE'].strftime('%d/%m')}: <b>{r['NAVN']}</b></span></div>", unsafe_allow_html=True)
            except: st.caption("Kunne ikke indlæse transfer-data")

    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>SCOUTING</span></div>', unsafe_allow_html=True)

    # --- 2. NEDERSTE SEKTION: Statistik (Forberedelse) ---
    hif_recent = df_stats[((df_stats['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID.strip().upper()) | (df_stats['CONTESTANTAWAY_OPTAUUID'].str.upper() == HIF_UUID.strip().upper())) & (df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=True).copy()
    
    if not hif_recent.empty:
        # Beregn kolonner
        hif_recent['PLOT_GOALS'] = hif_recent.apply(lambda r: r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['TOTAL_AWAY_SCORE'], axis=1)
        hif_recent['PLOT_XG'] = hif_recent.apply(lambda r: r['HOME_XG'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['AWAY_XG'], axis=1)
        hif_recent['PLOT_SHOTS'] = hif_recent.apply(lambda r: r['HOME_SHOTS'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['AWAY_SHOTS'], axis=1)
        hif_recent['PLOT_TOUCHES'] = hif_recent.apply(lambda r: r['HOME_TOUCHES'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['AWAY_TOUCHES'], axis=1)
        hif_recent['PLOT_POSS'] = hif_recent.apply(lambda r: r['HOME_POSS'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['AWAY_POSS'], axis=1)
        hif_recent['PLOT_FWD'] = hif_recent.apply(lambda r: r['HOME_FORWARD_PASSES'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['AWAY_FORWARD_PASSES'], axis=1)
        hif_recent = hif_recent.reset_index(drop=True)
        hif_recent['index'] = hif_recent.index + 1
        hif_recent['TOOLTIP_VS'] = hif_recent.apply(lambda r: (r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['CONTESTANTHOME_NAME']) + (" (H)" if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else " (U)"), axis=1)

        metrics = [
            {"name": "Mål", "col": "PLOT_GOALS", "fmt": ".0f"}, 
            {"name": "xG", "col": "PLOT_XG", "fmt": ".2f"}, 
            {"name": "Skud", "col": "PLOT_SHOTS", "fmt": ".0f"}, 
            {"name": "Touches", "col": "PLOT_TOUCHES", "fmt": ".0f"}, 
            {"name": "Possession", "col": "PLOT_POSS", "fmt": ".1f"}, 
            {"name": "Fwd Passes", "col": "PLOT_FWD", "fmt": ".0f"}
        ]

        # --- 3. NY SEKTION: Tabel og Trendlines ---
        st.divider()
        t_col1, t_col2, t_col3 = st.columns([2, 1, 1])

        with t_col1:
            st.markdown("###### Hvidovre IF - Sæsonoversigt")
            df_display = hif_recent[['index', 'PLOT_GOALS', 'PLOT_XG', 'PLOT_SHOTS', 'PLOT_TOUCHES', 'PLOT_POSS', 'PLOT_FWD']].copy()
            df_display.columns = ['Runde', 'Mål', 'xG', 'Skud', 'Touches', 'Poss %', 'Fwd Passes']
            st.dataframe(df_display, hide_index=True, use_container_width=True)

        def byg_chart(metric):
            col = metric['col']
            base = alt.Chart(hif_recent).encode(x='index:O', y=f'{col}:Q', tooltip=['TOOLTIP_VS', alt.Tooltip(col, title=metric['name'], format=metric['fmt'])]).properties(height=100)
            return (base.mark_line(color='#cccccc', strokeWidth=2) + base.mark_circle(size=50, color='#C41E3A') + alt.Chart(hif_recent).mark_rule(color='#333333', strokeDash=[4,4]).encode(y=f'mean({col}):Q')).interactive()

        with t_col2:
            st.caption(f"xG (Snit: {hif_recent['PLOT_XG'].mean():.2f})")
            st.altair_chart(byg_chart(metrics[1]), use_container_width=True)
            st.caption(f"Skud (Snit: {hif_recent['PLOT_SHOTS'].mean():.0f})")
            st.altair_chart(byg_chart(metrics[2]), use_container_width=True)

        with t_col3:
            st.caption(f"Touches (Snit: {hif_recent['PLOT_TOUCHES'].mean():.0f})")
            st.altair_chart(byg_chart(metrics[3]), use_container_width=True)
            st.caption(f"Possession (Snit: {hif_recent['PLOT_POSS'].mean():.1f})")
            st.altair_chart(byg_chart(metrics[4]), use_container_width=True)
                    
if __name__ == "__main__":
    vis_side()
