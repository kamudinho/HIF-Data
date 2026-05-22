import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn
import datetime

# --- (Din vis_transfer_dialog og apply_custom_style forbliver uændrede, men indsæt dem her som normalt) ---

def beregn_hold_stats(df_stats, team_uuid):
    """
    Hjælpefunktion der tager team_stats dataframe og udregner 
    sæsongennemsnit for Mål, xG og Possession per kamp for et givent hold.
    """
    # Find kun de kampe der rent faktisk er spillet
    played = df_stats[df_stats['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
    
    home = played[played['CONTESTANTHOME_OPTAUUID'].str.upper() == team_uuid.upper()]
    away = played[played['CONTESTANTAWAY_OPTAUUID'].str.upper() == team_uuid.upper()]
    
    total_matches = len(home) + len(away)
    if total_matches == 0:
        return {"gf": "0.0", "ga": "0.0", "xgf": "0.0", "xga": "0.0", "poss": "0"}
        
    # Totale Mål
    gf = home['TOTAL_HOME_SCORE'].sum() + away['TOTAL_AWAY_SCORE'].sum()
    ga = home['TOTAL_AWAY_SCORE'].sum() + away['TOTAL_HOME_SCORE'].sum()
    
    # Totale xG (bruger fillna(0) for en sikkerheds skyld, hvis Opta mangler data på en kamp)
    xgf = home['HOME_XG'].fillna(0).sum() + away['AWAY_XG'].fillna(0).sum()
    xga = home['AWAY_XG'].fillna(0).sum() + away['HOME_XG'].fillna(0).sum()
    
    # Snit Possession
    poss_all = pd.concat([home['HOME_POSS'], away['AWAY_POSS']]).dropna().mean()
    
    return {
        "gf": f"{gf / total_matches:.1f}",
        "ga": f"{ga / total_matches:.1f}",
        "xgf": f"{xgf / total_matches:.2f}",
        "xga": f"{xga / total_matches:.2f}",
        "poss": f"{int(round(poss_all))}%" if pd.notnull(poss_all) else "0%"
    }


def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    DB, LIGA_UUID, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "dyjr458hcmrcy87fsabfsy87o", "8GXD9RY2580PU1B1DD5NY9YMY"
    
    # Sørg for at du har importeret get_opta_queries i toppen af din fil, eller at den ligger tilgængelig i samme script.
    # Vi henter din Team Stats query til NordicBet Liga
    queries = get_opta_queries("NordicBet Liga", "2025/2026", hif_only=False)
    
    # Indlæs Matchinfo + Team Stats
    df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    
    df_stats = conn.query(queries["opta_team_stats"])
    df_stats.columns = [str(c).upper() for c in df_stats.columns]

    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    # Gør datoerne mere håndterbare og sørg for de er timezone-naive til sammenligning
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce').dt.tz_localize(None)

    col1, col2, col3 = st.columns([1, 1, 1])

    # 1. COL1: Næste kamp, Metrics, Legends
    with col1:
        with st.container(border=True):
            hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID.strip().upper()) | 
                               (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == HIF_UUID.strip().upper())]
            
            # --- FIX: NÆSTE MODSTANDER ---
            # Vi filtrerer på dags dato, så vi ikke kun er afhængige af at Opta har sat status til 'Fixture'. 
            # Derved undgår vi visningsfejl, hvis der mangler statusopdateringer.
            today = pd.Timestamp.today().normalize()
            future = hif_m[hif_m['MATCH_DATE_FULL'] >= today].sort_values('MATCH_DATE_FULL')

            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['CONTESTANTAWAY_OPTAUUID'] if str(nk['CONTESTANTHOME_OPTAUUID']).upper() == HIF_UUID.strip().upper() else nk['CONTESTANTHOME_OPTAUUID']
                opp_name = opta_to_name.get(str(opp_id).upper(), "Ukendt")

                st.markdown(f"<div class='card-title'><span>NÆSTE KAMP vs. {opp_name.upper()}</span><span class='title-date'>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</span></div>", unsafe_allow_html=True)

                t_l, t_r = st.columns([1, 1.2]) 
                with t_l:
                    c1, c2, c3 = st.columns([1, 0.8, 1])
                    c1.image(TEAMS.get("Hvidovre", {}).get("logo", ""), width=38)
                    c2.markdown("<div style='text-align:center; padding-top:10px; font-size:9px; color:#888;'>VS</div>", unsafe_allow_html=True)
                    c3.image(TEAMS.get(opp_name, {}).get("logo", ""), width=38)
                
                # --- FIX: DYNAMISKE METRICS ---
                # Beregn data for begge hold
                hif_stats = beregn_hold_stats(df_stats, HIF_UUID)
                opp_stats = beregn_hold_stats(df_stats, opp_id)

                with t_r:
                    # HTML-tabellen udvides lidt, så den sammenligner Hvidovre vs Næste Modstander
                    stats_html = f"""
                    <table class='stats-table'>
                        <tr>
                            <td class='stats-label' style='padding-bottom: 4px;'></td>
                            <td class='stats-value' style='font-size:8px; color:#dc3545; padding-bottom: 4px;'>HIF</td>
                            <td class='stats-value' style='font-size:8px; color:#666; padding-bottom: 4px;'>{opp_name[:3].upper()}</td>
                        </tr>
                        <tr>
                            <td class='stats-label'>Mål f/i</td>
                            <td class='stats-value'>{hif_stats['gf']}/{hif_stats['ga']}</td>
                            <td class='stats-value'>{opp_stats['gf']}/{opp_stats['ga']}</td>
                        </tr>
                        <tr>
                            <td class='stats-label'>xG f/i</td>
                            <td class='stats-value'>{hif_stats['xgf']}/{hif_stats['xga']}</td>
                            <td class='stats-value'>{opp_stats['xgf']}/{opp_stats['xga']}</td>
                        </tr>
                        <tr>
                            <td class='stats-label'>Poss.</td>
                            <td class='stats-value'>{hif_stats['poss']}</td>
                            <td class='stats-value'>{opp_stats['poss']}</td>
                        </tr>
                    </table>
                    """
                    st.markdown(stats_html, unsafe_allow_html=True)

                # Legends logik forbliver uændret
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
                for _, r in df_t.sort_values('TS_DATE', ascending=False).head(5).iterrows():
                    dato_str = r['TS_DATE'].strftime('%d/%m')
                    st.markdown(f"""
                        <div class='list-item'>
                            <span class='player-info'>{dato_str}: <b>{r['NAVN']}</b> ({r['POSITION']})</span>
                            <span class='prev-club'>{r.get('SENESTE_KLUB', '?')}</span>
                            <span>➔</span>
                            <span class='new-club'>{r.get('KLUB', '?')}</span>
                        </div>
                    """, unsafe_allow_html=True)
                if st.button("Se alle transfers", key="transfers_btn", use_container_width=True):
                    vis_transfer_dialog(df_t)
            except Exception as e:
                st.caption("Kunne ikke indlæse transfer-data")

    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>SCOUTING</span></div>', unsafe_allow_html=True)
