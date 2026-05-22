import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn
import datetime

def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            [data-testid="stHeader"] { background: rgba(0,0,0,0); }
            .stApp { background-color: #FFFFFF; }
            [data-testid="stVerticalBlockBorderWrapper"] { min-height: 350px; }
            .card-title { color: #1a1a1a; font-size: 11px; font-weight: 700; margin-bottom: 15px; text-transform: uppercase; display: flex; justify-content: space-between; border-bottom: 1px solid #f0f0f0; padding-bottom: 8px; }
            .title-date { color: #888; font-weight: 500; text-transform: none; font-size: 11px; }
            .stats-table { width: 95%; font-size: 10px; border-collapse: collapse; margin-left: auto; }
            .stats-table tr, .stats-table td { border: none !important; padding: 4px 0; }
            .stats-label { color: #666; font-weight: 500; }
            .stats-value { text-align: right; font-weight: 700; color: #111; }
            .form-wrapper { display: flex; justify-content: space-between; gap: 8px; width: 100%; margin-top: 20px; }
            .form-column { display: flex; flex-direction: column; align-items: center; flex: 1; }
            .res-pill { width: 100%; border-radius: 4px; color: white; text-align: center; font-size: 10px; font-weight: 800; padding: 4px 0; margin-bottom: 6px; }
            .legend-logo { width: 26px; height: 26px; object-fit: contain; }
            .list-item { font-size: 11px; margin-bottom: 5px; color: #333; line-height: 1.2; }
        </style>
    """, unsafe_allow_html=True)

def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    DB, LIGA_UUID, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "dyjr458hcmrcy87fsabfsy87o", "8GXD9RY2580PU1B1DD5NY9YMY"
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = HIF_UUID.strip().upper()
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    col1, col2, col3 = st.columns([1, 1, 1])

    # 1. NÆSTE KAMP + METRICS + LEGENDS
    with col1:
        with st.container(border=True):
            # Definer future her, så den altid eksisterer
            hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == hif_id) | (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == hif_id)]
            future = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL')
            
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['CONTESTANTAWAY_OPTAUUID'] if str(nk['CONTESTANTHOME_OPTAUUID']).upper() == hif_id else nk['CONTESTANTHOME_OPTAUUID']
                opp_name = opta_to_name.get(str(opp_id).upper(), "Ukendt")
                
                st.markdown(f"<div class='card-title'><span>NÆSTE KAMP vs. {opp_name.upper()}</span><span class='title-date'>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</span></div>", unsafe_allow_html=True)
                
                # Layout: Logoer (venstre) | Metrics (højre)
                t_main_l, t_main_r = st.columns([1, 1.5])
                
                with t_main_l:
                    c1, c2, c3 = st.columns([1, 0.5, 1])
                    c1.image(TEAMS.get("Hvidovre", {}).get("logo", ""), width=42)
                    c2.markdown("<div style='text-align:center; padding-top:10px; font-size:10px; color:#ccc;'><b>VS</b></div>", unsafe_allow_html=True)
                    c3.image(TEAMS.get(opp_name, {}).get("logo", ""), width=42)
                
                with t_main_r:
                    st.markdown(f"""
                        <table class='stats-table' style='margin-top:0px;'>
                            <tr><td class='stats-label'>Mål f/i</td><td class='stats-value'>1.4/1.1</td></tr>
                            <tr><td class='stats-label'>xG f/i</td><td class='stats-value'>1.5/1.2</td></tr>
                            <tr><td class='stats-label'>Poss.</td><td class='stats-value'>52%</td></tr>
                        </table>
                    """, unsafe_allow_html=True)

                # Form-bar med logoer
                st.markdown(f"<div style='font-size:10px; color:#888; font-weight:700; margin-top:14px; text-transform:uppercase;'>Form: {opp_name}</div>", unsafe_allow_html=True)
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
            else:
                st.write("Ingen kommende kampe fundet.")
    # 2. TRANSFERS 
    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>TRANSFERS</span></div>', unsafe_allow_html=True)
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv")
                df_t = df_t.dropna(subset=['TIMESTAMP'])
                df_t['TS_SORT'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
                # Sorter og tag de 7 nyeste
                df_display = df_t.sort_values('TS_SORT', ascending=False).head(7)
                
                for _, r in df_display.iterrows():
                    # Formatering: Dato: Klub - Navn (Position)
                    dato_str = pd.to_datetime(r['TIMESTAMP']).strftime('%d/%m')
                    klub = r['KLUB']
                    navn = r['NAVN']
                    pos = r.get('POSITION', '-') # Henter position hvis den findes
                    
                    st.markdown(f"""
                        <div class='list-item'>
                            {dato_str}: <b>{klub}</b> - {navn} ({pos})
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
                if st.button("Se alle transfers", use_container_width=True):
                    vis_transfer_dialog(df_t)
            except Exception as e:
                st.caption("Kunne ikke indlæse transfers")

    # 3. SCOUTING
    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>SCOUTING</span></div>', unsafe_allow_html=True)
            # (Din scouting logik)
