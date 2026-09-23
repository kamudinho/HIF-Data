# HIF-head.py
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
from data.sql.teams import hent_hoved_stats, hent_samlet_hold_statistik

def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            .stApp { background-color: #FFFFFF; }
            
            div.top-section-container [data-testid="stHorizontalBlock"] {
                display: flex;
                align-items: stretch;
            }
            div.top-section-container [data-testid="stHorizontalBlock"] > div:nth-child(1) {
                flex: 1 1 24% !important; max-width: 24% !important;
            }
            div.top-section-container [data-testid="stHorizontalBlock"] > div:nth-child(2) {
                flex: 1 1 52% !important; max-width: 52% !important;
            }
            div.top-section-container [data-testid="stHorizontalBlock"] > div:nth-child(3) {
                flex: 1 1 24% !important; max-width: 24% !important;
            }

            .stats-table { width: 100%; font-size: 11px; border-collapse: collapse; table-layout: auto; }
            .stats-table th { text-align: center; padding: 4px; color: #888; font-weight: 600; white-space: nowrap; }
            .stats-label { text-align: left !important; color: #666; font-weight: 700; width: 30%; padding: 4px 4px 4px 0; }
            .stats-value { text-align: center !important; font-weight: 700; color: #111; padding: 4px 2px; min-width: 20px; }
            .card-title { color: #1a1a1a; font-size: 11px; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; border-bottom: 1px solid #f0f0f0; padding-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
            
            .table-standings { width: 100%; font-size: 11px; border-collapse: collapse; }
            .table-standings th { text-align: center; padding: 4px 2px; color: #888; border-bottom: 1px solid #eee; font-weight: 600; }
            .table-standings td { padding: 4px 2px; text-align: center; color: #333; font-weight: 600; }
            .table-standings .team-cell { text-align: left; font-weight: 700; color: #111; }
            .table-standings .hif-row { background-color: #ffebe8; }

            .hover-parent { position: relative; display: inline-block; cursor: help; }
            .hover-child {
                visibility: hidden; width: 220px; background-color: #333; color: #fff;
                text-align: left; padding: 8px 10px; border-radius: 4px; position: absolute;
                z-index: 1000; bottom: 125%; left: 50%; margin-left: -110px; opacity: 0;
                transition: opacity 0.2s ease-in-out; font-size: 11px; font-weight: normal;
                box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
            }
            .hover-parent:hover .hover-child { visibility: visible; opacity: 1; }
        </style>
    """, unsafe_allow_html=True)

def resolve_team_name(uuid_str, raw_name=""):
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

def beregn_kategori_indices(row, hif_uuid):
    is_home = str(row['CONTESTANTHOME_OPTAUUID']).strip().upper() == hif_uuid.strip().upper()
    def get_val(col_h, col_a):
        val = row[col_h] if is_home else row[col_a]
        return float(val) if pd.notnull(val) else 0.0
    
    xg, shots, touches = get_val('HOME_XG', 'AWAY_XG'), get_val('HOME_SHOTS', 'AWAY_SHOTS'), get_val('HOME_TOUCHES', 'AWAY_TOUCHES')
    tackles, goals_con = get_val('HOME_TACKLES', 'AWAY_TACKLES'), get_val('TOTAL_AWAY_SCORE', 'TOTAL_HOME_SCORE')
    goals_for = get_val('TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE')
    xg_against = get_val('AWAY_XG', 'HOME_XG')

    corners_for = get_val('HOME_CORNERS_WON', 'AWAY_CORNERS_WON')
    corners_against = get_val('AWAY_CORNERS_WON', 'HOME_CORNERS_WON')
    fouls_won = get_val('HOME_FOULS_WON', 'AWAY_FOULS_WON')
    fouls_lost = get_val('AWAY_FOULS_LOST', 'HOME_FOULS_LOST')

    off_idx = (xg * 1.5) + (shots * 0.3) + (touches * 0.05)
    def_idx = -(goals_con * 2.0) + (tackles * 0.2)
    off_std = (goals_for * 3.0) + (xg * 1.0) + (corners_for * 0.3) + (fouls_won * 0.2)
    def_std = -(goals_con * 3.0) - (xg_against * 1.0) - (corners_against * 0.3) - (fouls_lost * 0.2)

    return pd.Series({'Offensiv': off_idx, 'Defensiv': def_idx, 'Off_Std': off_std, 'Def_Std': def_std})

def beregn_per_90(df_stats, team_uuid):
    if df_stats is None or df_stats.empty: return None, ""
    played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    if played.empty: return None, ""

    zero_fill_cols = ['TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'HOME_XG', 'AWAY_XG', 'HOME_OFF_TARGET', 'AWAY_OFF_TARGET', 'HOME_THROWS', 'AWAY_THROWS', 'HOME_FOULS_WON', 'AWAY_FOULS_WON', 'HOME_CORNERS_WON', 'AWAY_CORNERS_WON', 'HOME_TACKLES', 'AWAY_TACKLES', 'HOME_CLEARANCES', 'AWAY_CLEARANCES', 'HOME_PASSES', 'AWAY_PASSES']
    for col in zero_fill_cols:
        if col in played.columns:
            played[col] = pd.to_numeric(played[col], errors='coerce').fillna(0)

    for col in ['HOME_POSSESSION', 'AWAY_POSSESSION']:
        if col in played.columns:
            played[col] = pd.to_numeric(played[col], errors='coerce')

    hif_matches = played[((played['CONTESTANTHOME_OPTAUUID'].str.upper() == team_uuid.upper()) | (played['CONTESTANTAWAY_OPTAUUID'].str.upper() == team_uuid.upper()))].sort_values('MATCH_DATE_FULL')
    if len(hif_matches) == 0: return None, ""

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
        STAT_TYPE_MAP["wonCorners"]: ('HOME_CORNERS_WON', 'AWAY_CORNERS_WON'),
        STAT_TYPE_MAP["totalThrows"]: ('HOME_THROWS', 'AWAY_THROWS'),
        STAT_TYPE_MAP["fkFoulWon"]: ('HOME_FOULS_WON', 'AWAY_FOULS_WON')
    }
    
    results = []
    for display_name, (h_col, a_col) in stats_map.items():
        hif_vals = []
        for _, r in hif_matches.iterrows():
            if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == team_uuid.strip().upper():
                val = r[h_col]
            else:
                val = r[a_col]
            if pd.notnull(val): hif_vals.append(val)
        hif_val = sum(hif_vals) / len(hif_vals) if hif_vals else 0.0

        if is_home:
            last_val = last_match[h_col] if h_col in last_match else 0.0
        else:
            last_val = last_match[a_col] if a_col in last_match else 0.0
        last_val = float(last_val) if pd.notnull(last_val) else 0.0

        liga_val = pd.concat([played[h_col], played[a_col]]).mean()
        
        diff_vs_liga = hif_val - liga_val
        diff_vs_hif = last_val - hif_val 
        
        results.append({
            "Stat": display_name, "HIF": hif_val, "Liga": liga_val, 
            "Diff_Liga": diff_vs_liga, "Seneste": last_val, 
            "Diff_vs_Hif": diff_vs_hif
        })
        
    return pd.DataFrame(results), opp_name

def beregn_hold_per_90_stats(df_stats, team_uuid):
    """Beregner præcis de samme per-90 gennemsnit direkte fra df_stats til brug i næste modstander-kortet."""
    if df_stats is None or df_stats.empty: 
        return {"poss": "0.0%", "gf": "0.00", "ga": "0.00", "xgf": "0.00", "xga": "0.00"}
    
    played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
    if played.empty: 
        return {"poss": "0.0%", "gf": "0.00", "ga": "0.00", "xgf": "0.00", "xga": "0.00"}

    zero_fill_cols = ['TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'HOME_XG', 'AWAY_XG', 'HOME_POSSESSION', 'AWAY_POSSESSION']
    for col in zero_fill_cols:
        if col in played.columns:
            played[col] = pd.to_numeric(played[col], errors='coerce').fillna(0)

    team_matches = played[((played['CONTESTANTHOME_OPTAUUID'].str.upper() == team_uuid.upper()) | (played['CONTESTANTAWAY_OPTAUUID'].str.upper() == team_uuid.upper()))]
    if len(team_matches) == 0: 
        return {"poss": "0.0%", "gf": "0.00", "ga": "0.00", "xgf": "0.00", "xga": "0.00"}

    poss_vals, gf_vals, ga_vals, xgf_vals, xga_vals = [], [], [], [], []

    for _, r in team_matches.iterrows():
        is_home = str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == team_uuid.strip().upper()
        
        poss = r['HOME_POSSESSION'] if is_home else r['AWAY_POSSESSION']
        gf = r['TOTAL_HOME_SCORE'] if is_home else r['TOTAL_AWAY_SCORE']
        ga = r['TOTAL_AWAY_SCORE'] if is_home else r['TOTAL_HOME_SCORE']
        xgf = r['HOME_XG'] if is_home else r['AWAY_XG']
        xga = r['AWAY_XG'] if is_home else r['HOME_XG']

        if pd.notnull(poss): poss_vals.append(poss)
        if pd.notnull(gf): gf_vals.append(gf)
        if pd.notnull(ga): ga_vals.append(ga)
        if pd.notnull(xgf): xgf_vals.append(xgf)
        if pd.notnull(xga): xga_vals.append(xga)

    avg_poss = sum(poss_vals) / len(poss_vals) if poss_vals else 0.0
    avg_gf = sum(gf_vals) / len(gf_vals) if gf_vals else 0.0
    avg_ga = sum(ga_vals) / len(ga_vals) if ga_vals else 0.0
    avg_xgf = sum(xgf_vals) / len(xgf_vals) if xgf_vals else 0.0
    avg_xga = sum(xga_vals) / len(xga_vals) if xga_vals else 0.0

    return {
        "poss": f"{avg_poss:.1f}%",
        "gf": f"{avg_gf:.2f}",
        "ga": f"{avg_ga:.2f}",
        "xgf": f"{avg_xgf:.2f}",
        "xga": f"{avg_xga:.2f}"
    }
    
def beregn_stilling(df_matches, valgt_saeson, valgt_turnering):
    stats = {}
    saesons_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, [])
    if not saesons_hold: saesons_hold = sorted(TEAMS.keys())

    for name in saesons_hold:
        stats[name] = {'K': 0, 'V': 0, 'U': 0, 'T': 0, 'MF': 0, 'GF': 0, 'P': 0}

    if df_matches is not None and not df_matches.empty and 'MATCH_STATUS' in df_matches.columns:
        played = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()
        for _, row in played.iterrows():
            h_uuid = str(row['CONTESTANTHOME_OPTAUUID']).upper()
            a_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).upper()
            h_name = resolve_team_name(h_uuid, row.get('CONTESTANTHOME_NAME', ''))
            a_name = resolve_team_name(a_uuid, row.get('CONTESTANTAWAY_NAME', ''))
            
            if h_name not in stats: stats[h_name] = {'K': 0, 'V': 0, 'U': 0, 'T': 0, 'MF': 0, 'GF': 0, 'P': 0}
            if a_name not in stats: stats[a_name] = {'K': 0, 'V': 0, 'U': 0, 'T': 0, 'MF': 0, 'GF': 0, 'P': 0}

            try:
                h_g = int(row['TOTAL_HOME_SCORE'])
                a_g = int(row['TOTAL_AWAY_SCORE'])
            except:
                continue

            stats[h_name]['K'] += 1; stats[a_name]['K'] += 1
            stats[h_name]['MF'] += (h_g - a_g); stats[a_name]['MF'] += (a_g - h_g)
            stats[h_name]['GF'] += h_g; stats[a_name]['GF'] += a_g

            if h_g > a_g:
                stats[h_name]['V'] += 1; stats[h_name]['P'] += 3; stats[a_name]['T'] += 1
            elif a_g > h_g:
                stats[a_name]['V'] += 1; stats[a_name]['P'] += 3; stats[h_name]['T'] += 1
            else:
                stats[h_name]['U'] += 1; stats[a_name]['U'] += 1
                stats[h_name]['P'] += 1; stats[a_name]['P'] += 1

    df_standings = pd.DataFrame.from_dict(stats, orient='index').reset_index()
    df_standings.columns = ['Hold', 'K', 'V', 'U', 'T', 'MF', 'GF', 'P']
    df_standings = df_standings.sort_values(by=['P', 'MF', 'GF', 'Hold'], ascending=[False, False, False, True]).reset_index(drop=True)
    df_standings.index = df_standings.index + 1
    return df_standings

def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return
    
    HIF_UUID = TEAMS.get("Hvidovre", {}).get("opta_uuid", "8gxd9ry2580pu1b1dd5ny9ymy").upper()
    
    active_season = DEFAULT_SEASON
    active_comp = DEFAULT_COMP
    calendar_uuid = SEASONS.get(active_season, {}).get(active_comp)

    df_stats = hent_hoved_stats(conn, calendar_uuid)
    df_hold_stats = hent_samlet_hold_statistik(conn, calendar_uuid)
    df_matches = df_stats.copy()

    # --- TOPSEKTION ---
    st.markdown('<div class="top-section-container">', unsafe_allow_html=True)
    with st.container(border=True):
        col1, col2, col3 = st.columns([1, 2.2, 1])

        # KOLONNE 1: NÆSTE MODSTANDER
        with col1:
            st.markdown("<div class='card-title'><span>NÆSTE MODSTANDER</span></div>", unsafe_allow_html=True)
            
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
                
                match_date = nk['MATCH_DATE_FULL'].strftime('%d/%m/%Y') if pd.notnull(nk['MATCH_DATE_FULL']) else ""
                match_time = nk.get('MATCH_LOCALTIME', '') or nk.get('MATCH_TIME', '')
                venue = nk.get('VENUE_LONGNAME', 'Ukendt stadion')
                round_week = nk.get('WEEK', '')
                
                st.markdown(f"<div class='card-title' style='border:none; margin-top:0px; padding-bottom:0; font-size: 13px;'><span>vs. {opp_name.upper()}</span><span>{match_date} kl. {match_time}</span></div>", unsafe_allow_html=True)
                
                meta_html = f"""
                <div style='font-size: 11px; color: #555; margin-bottom: 8px; line-height: 1.4;'>
                    <b>Stadion:</b> {venue}<br>
                    <b>Runde:</b> Spillerunde {round_week}<br>
                </div>
                """
                st.markdown(meta_html, unsafe_allow_html=True)
                
                # Brug præcis samme per-90 beregningslogik til næste modstander-kortet
                hif_stats = beregn_hold_per_90_stats(df_stats, HIF_UUID)
                opp_stats = beregn_hold_per_90_stats(df_stats, opp_id)
                
                hif_logo = TEAMS.get("Hvidovre", {}).get("logo", "")
                opp_logo = TEAMS.get(opp_name, {}).get("logo", "")
                
                stats_html = f"""
                <table class='stats-table' style='width: 100%; margin-top: 4px;'>
                    <tr><td style='width: 34%;'></td>
                        <td style='text-align: center; width: 33%; border-bottom: 1px solid #eee; padding-bottom: 4px;'><img src='{hif_logo}' style='width: 22px; height: 22px; object-fit: contain;'></td>
                        <td style='text-align: center; width: 33%; border-bottom: 1px solid #eee; padding-bottom: 4px;'><img src='{opp_logo}' style='width: 22px; height: 22px; object-fit: contain;'></td>
                    </tr>
                    <tr><td class='stats-label'>Besiddelse</td><td class='stats-value'>{hif_stats.get('poss', '-')}</td><td class='stats-value'>{opp_stats.get('poss', '-')}</td></tr>
                    <tr><td class='stats-label'>Mål for/imod</td><td class='stats-value'>{hif_stats.get('gf', '0')}/{hif_stats.get('ga', '0')}</td><td class='stats-value'>{opp_stats.get('gf', '0')}/{opp_stats.get('ga', '0')}</td></tr>
                    <tr><td class='stats-label'>xG for/imod</td><td class='stats-value'>{hif_stats.get('xgf', '0')}/{hif_stats.get('xga', '0')}</td><td class='stats-value'>{opp_stats.get('xgf', '0')}/{opp_stats.get('xga', '0')}</td></tr>
                </table>"""
                st.markdown(stats_html, unsafe_allow_html=True)
            else:
                st.caption(f"Afventer næste kamp for sæson {active_season}")
                
        # KOLONNE 2: HVIDOVRE IF vs. LIGA
        with col2:
            c_title, c_icon = st.columns([12, 1])
            with c_title:
                st.markdown("<div class='card-title' style='border:none; margin-bottom:0;'><span>HVIDOVRE IF vs. LIGA</span></div>", unsafe_allow_html=True)
            with c_icon:
                st.markdown("""
                    <div class="hover-parent" style="float: right;">
                        ℹ️
                        <div class="hover-child">
                            <b>Om denne oversigt</b><br>
                            Sammenligner Hvidovres per-90-minutters nøgletal mod ligaens gennemsnit samt den seneste modstander.<br>
                            - <b>Diff vs Liga:</b> Afvigelse mellem HIF-snit og liga-snit.<br>
                            - <b>Diff vs HIF:</b> Sidste kamps afvigelse fra HIFs eget snit.
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='border-bottom: 1px solid #f0f0f0; margin-bottom: 8px;'></div>", unsafe_allow_html=True)
            
            df_stats_comp, opp_navn = beregn_per_90(df_stats, HIF_UUID)
            if df_stats_comp is not None:
                opp_header = f"vs. {opp_navn}"
                
                html = f"<table class='stats-table'><thead><tr><th></th><th>{opp_header}</th><th>Diff vs HIF</th><th>HIF</th><th>Liga</th><th>Diff</th></tr></thead><tbody>"
                for _, r in df_stats_comp.iterrows():
                    diff_liga_color = "#28a745" if r['Diff_Liga'] > 0 else "#dc3545"
                    diff_hif_color = "#28a745" if r['Diff_vs_Hif'] > 0 else "#dc3545"
                    
                    if "besiddelse" in r['Stat'].lower():
                        hif_str = f"{r['HIF']:.1f}%"; liga_str = f"{r['Liga']:.1f}%"; last_str = f"{r['Seneste']:.1f}%"
                    elif "goals" in r['Stat'].lower() or "xg" in r['Stat'].lower():
                        hif_str = f"{r['HIF']:.2f}"; liga_str = f"{r['Liga']:.2f}"; last_str = f"{r['Seneste']:.2f}"
                    else:
                        hif_str = f"{r['HIF']:.2f}"; liga_str = f"{r['Liga']:.2f}"; last_str = f"{r['Seneste']:.0f}"

                    html += f"""<tr>
                        <td class='stats-label'>{r['Stat']}</td>
                        <td class='stats-value'>{last_str}</td>
                        <td class='stats-value' style='color:{diff_hif_color}; font-weight:800;'>{r['Diff_vs_Hif']:+.2f}</td>
                        <td class='stats-value'>{hif_str}</td>
                        <td class='stats-value'>{liga_str}</td>
                        <td class='stats-value' style='color:{diff_liga_color}; font-weight:800;'>{r['Diff_Liga']:+.2f}</td>
                    </tr>"""
                html += "</tbody></table>"
                st.markdown(html, unsafe_allow_html=True)

        # KOLONNE 3: STILLING
        with col3:
            st.markdown(f"<div class='card-title'><span>STILLING ({active_comp.upper()})</span></div>", unsafe_allow_html=True)
            
            df_stilling = beregn_stilling(df_matches, active_season, active_comp)
            if not df_stilling.empty:
                table_html = "<table class='table-standings'><thead><tr><th style='text-align:left;'>Hold</th><th>K</th><th>MF</th><th>P</th></tr></thead><tbody>"
                for idx, row in df_stilling.head(12).iterrows():
                    row_class = "hif-row" if "Hvidovre" in row['Hold'] else ""
                    mf_sign = f"+{row['MF']}" if row['MF'] > 0 else str(row['MF'])
                    table_html += f"<tr class='{row_class}'><td>{idx}</td><td class='team-cell'>{row['Hold']}</td><td>{row['K']}</td><td>{mf_sign}</td><td><b>{row['P']}</b></td></tr>"
                table_html += "</tbody></table>"
                st.markdown(table_html, unsafe_allow_html=True)
            else:
                st.caption("Ingen stillingsdata fundet.")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- BUNDSEKTION: TRENDGRAFER ---
    with st.container(border=True):
        st.markdown('<div class="card-title"><span>PRÆSTATION-TRENDS (Seneste 10 kampe)</span></div>', unsafe_allow_html=True)
        hif_recent = df_stats[((df_stats['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID) | (df_stats['CONTESTANTAWAY_OPTAUUID'].str.upper() == HIF_UUID)) & (df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=True).tail(10).copy()
        
        if not hif_recent.empty:
            num_cols = ['HOME_XG', 'AWAY_XG', 'HOME_SHOTS', 'AWAY_SHOTS', 'HOME_TOUCHES', 'AWAY_TOUCHES', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'HOME_CORNERS_WON', 'AWAY_CORNERS_WON', 'HOME_FOULS_WON', 'AWAY_FOULS_WON', 'HOME_AERIAL_WON', 'AWAY_AERIAL_WON', 'HOME_TACKLES', 'AWAY_TACKLES']
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
                ("OFFENSIV", "Offensiv", "xG, Skud, Touches i modstanderens felt", r1_c1), 
                ("DEFENSIV", "Defensiv", "Mål imod, defensive tacklinger", r1_c2), 
                ("OFF. STD", "Off_Std", "Mål, xG og standarder (hjørner/frispark) for", r2_c1), 
                ("DEF. STD", "Def_Std", "Mål, xG og standarder (hjørner/frispark) imod", r2_c2)
            ]
            
            for title, col, desc, target in categories:
                with target:
                    g_title, g_icon = st.columns([12, 1])
                    with g_title:
                        st.markdown(f"<div style='font-weight:700; font-size:12px;'>{title}</div>", unsafe_allow_html=True)
                    with g_icon:
                        st.markdown(f"""
                            <div class="hover-parent" style="float: right;">
                                ℹ️
                                <div class="hover-child">
                                    <b>{title}</b><br>
                                    {desc}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    st.caption(f"<div style='margin-top:-8px; font-size:10px; margin-bottom:4px;'>{desc}</div>", unsafe_allow_html=True)
                    
                    hif_avg = hif_recent[col].mean()
                    hif_recent['tooltip_header'] = hif_recent.apply(lambda r: f"vs. {r['OPPONENT_NAME']} {int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])} ({r['HOME_OR_AWAY']})", axis=1)
                    hif_recent['diff_label'] = hif_recent[col].apply(lambda x: f"{x - hif_avg:+.1f}")
                    
                    line = alt.Chart(hif_recent).mark_line(color='#AAAAAA', point=alt.MarkConfig(color='#C41E3A', filled=True)).encode(
                        x=alt.X('index:O', axis=None), 
                        y=alt.Y(f'{col}:Q', axis=None, scale=alt.Scale(zero=False)), 
                        tooltip=[alt.Tooltip('tooltip_header', title='Kamp'), alt.Tooltip(f'{col}', title='Score', format='.2f'), alt.Tooltip('diff_label', title='Diff vs Snit')]
                    ).properties(height=120)
                    
                    st.altair_chart(line + alt.Chart(pd.DataFrame({'y': [hif_avg]})).mark_rule(color='#C41E3A', strokeDash=[3,3]).encode(y='y:Q') + alt.Chart(pd.DataFrame({'y': [liga_means[col]]})).mark_rule(color='#000000', strokeDash=[2,2], opacity=0.4).encode(y='y:Q'), use_container_width=True)

if __name__ == "__main__":
    vis_side()
