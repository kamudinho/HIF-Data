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
            .stats-table { width: 100%; font-size: 10px; border-collapse: collapse; table-layout: fixed; }
            .stats-label { color: #666; font-weight: 700; width: 60%; padding: 4px 0; }
            .stats-value { text-align: right; font-weight: 700; color: #111; padding: 4px 0; }
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
        MatchStatsPivot AS (SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID, MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION FROM {DB}.OPTA_MATCHSTATS WHERE MATCH_OPTAUUID IN ({match_id_subquery}) GROUP BY 1, 2)
        SELECT b.*, sh.XG AS HOME_XG, sh.SHOTS AS HOME_SHOTS, sh.TOUCHES_IN_BOX AS HOME_TOUCHES, sa.XG AS AWAY_XG, sa.SHOTS AS AWAY_SHOTS, sa.TOUCHES_IN_BOX AS AWAY_TOUCHES FROM MatchBase b LEFT JOIN ExpectedGoalsPivot sh ON b.MATCH_OPTAUUID = sh.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = sh.CONTESTANT_OPTAUUID LEFT JOIN ExpectedGoalsPivot sa ON b.MATCH_OPTAUUID = sa.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = sa.CONTESTANT_OPTAUUID ORDER BY b.MATCH_DATE_FULL DESC"""}

def beregn_hold_stats(df_stats, team_uuid):
    played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    home = played[played['CONTESTANTHOME_OPTAUUID'].str.upper() == team_uuid.upper()]
    away = played[played['CONTESTANTAWAY_OPTAUUID'].str.upper() == team_uuid.upper()]
    total_matches = len(home) + len(away)
    if total_matches == 0: return {"gf": "0.0", "ga": "0.0", "xgf": "0.0", "xga": "0.0", "poss": "0%"}
    gf = home['TOTAL_HOME_SCORE'].sum() + away['TOTAL_AWAY_SCORE'].sum()
    ga = home['TOTAL_AWAY_SCORE'].sum() + away['TOTAL_HOME_SCORE'].sum()
    xgf = home['HOME_XG'].fillna(0).sum() + away['AWAY_XG'].fillna(0).sum()
    xga = home['AWAY_XG'].fillna(0).sum() + away['HOME_XG'].fillna(0).sum()
    return {"gf": f"{gf / total_matches:.1f}", "ga": f"{ga / total_matches:.1f}", "xgf": f"{xgf / total_matches:.2f}", "xga": f"{xga / total_matches:.2f}", "poss": "0%"}

def beregn_per_90(df_stats, team_uuid):
    hif_matches = df_stats[((df_stats['CONTESTANTHOME_OPTAUUID'].str.upper() == team_uuid.upper()) | (df_stats['CONTESTANTAWAY_OPTAUUID'].str.upper() == team_uuid.upper())) & (df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].copy()
    if len(hif_matches) == 0: return None
    for col in ['TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'HOME_XG', 'AWAY_XG', 'HOME_SHOTS', 'AWAY_SHOTS', 'HOME_TOUCHES', 'AWAY_TOUCHES']:
        hif_matches[col] = pd.to_numeric(hif_matches[col], errors='coerce').fillna(0)
    stats = {
        "Mål": hif_matches.apply(lambda r: r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'].upper() == team_uuid.upper() else r['TOTAL_AWAY_SCORE'], axis=1).sum(),
        "xG": hif_matches.apply(lambda r: r['HOME_XG'] if r['CONTESTANTHOME_OPTAUUID'].upper() == team_uuid.upper() else r['AWAY_XG'], axis=1).sum(),
        "Skud": hif_matches.apply(lambda r: r['HOME_SHOTS'] if r['CONTESTANTHOME_OPTAUUID'].upper() == team_uuid.upper() else r['AWAY_SHOTS'], axis=1).sum(),
        "Touches": hif_matches.apply(lambda r: r['HOME_TOUCHES'] if r['CONTESTANTHOME_OPTAUUID'].upper() == team_uuid.upper() else r['AWAY_TOUCHES'], axis=1).sum()
    }
    return {k: v / len(hif_matches) for k, v in stats.items()}

def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return
    DB, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "8GXD9RY2580PU1B1DD5NY9YMY"
    queries = get_opta_queries("NordicBet Liga", "2025/2026", hif_only=False)
    df_stats = conn.query(queries["opta_team_stats"])
    df_stats.columns = [str(c).upper() for c in df_stats.columns]
    
    # Række 1: Næste kamp, Transfers, Scouting
    c1, c2, c3 = st.columns(3)
    with c1: st.container(border=True).markdown("<div class='card-title'><span>NÆSTE KAMP</span></div>", unsafe_allow_html=True)
    with c2: st.container(border=True).markdown('<div class="card-title"><span>TRANSFERS</span></div>', unsafe_allow_html=True)
    with c3: st.container(border=True).markdown('<div class="card-title"><span>SCOUTING</span></div>', unsafe_allow_html=True)

    # Række 2: Sæson Snit + Trendlines grid
    with st.container(border=True):
        st.markdown('<div class="card-title"><span>SÆSON SNIT & TRENDS</span></div>', unsafe_allow_html=True)
        # Hovedinddeling: 1 kolonne til Snit, 2 kolonner til Trends
        main_col, trend_area = st.columns([1, 2])
        
        per90 = beregn_per_90(df_stats, HIF_UUID)
        with main_col:
            st.metric("Nyt Snit", f"{sum(per90.values())/len(per90):.2f}" if per90 else "0.0")
        
        with trend_area:
            # 2x2 grid til grafer
            r1_c1, r1_c2 = st.columns(2)
            r2_c1, r2_c2 = st.columns(2)
            
            # Trend data beregning
            hif_recent = df_stats[((df_stats['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID.strip().upper()) | (df_stats['CONTESTANTAWAY_OPTAUUID'].str.upper() == HIF_UUID.strip().upper()))].copy()
            hif_recent['PLOT_GOALS'] = hif_recent.apply(lambda r: r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['TOTAL_AWAY_SCORE'], axis=1)
            hif_recent['PLOT_XG'] = hif_recent.apply(lambda r: r['HOME_XG'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['AWAY_XG'], axis=1)
            hif_recent['PLOT_SHOTS'] = hif_recent.apply(lambda r: r['HOME_SHOTS'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['AWAY_SHOTS'], axis=1)
            hif_recent['PLOT_TOUCHES'] = hif_recent.apply(lambda r: r['HOME_TOUCHES'] if r['CONTESTANTHOME_OPTAUUID'].upper() == HIF_UUID else r['AWAY_TOUCHES'], axis=1)
            hif_recent['index'] = range(1, len(hif_recent) + 1)
            
            metrics = [("Mål", "PLOT_GOALS", r1_c1), ("xG", "PLOT_XG", r1_c2), ("Skud", "PLOT_SHOTS", r2_c1), ("Touches", "PLOT_TOUCHES", r2_c2)]
            for name, col, target in metrics:
                with target:
                    st.caption(name)
                    st.altair_chart(alt.Chart(hif_recent).mark_line(color='#C41E3A').encode(x='index:O', y=f"{col}:Q").properties(height=100), use_container_width=True)

if __name__ == "__main__":
    vis_side()
