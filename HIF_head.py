import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn

def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            [data-testid="stHeader"] { background: rgba(0,0,0,0); }
            .stApp { background-color: #FFFFFF; }
            .stVizColumns { gap: 1rem; }
            [data-testid="stVerticalBlockBorderWrapper"] { min-height: 350px; }

            .card-title {
                color: #1a1a1a;
                font-size: 11px;
                font-weight: 700;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #f0f0f0;
                padding-bottom: 8px;
            }
            
            .title-date { color: #888; font-weight: 500; text-transform: none; font-size: 11px; }

            .stats-table {
                width: 95%;
                font-size: 10px;
                border-collapse: collapse;
                margin-left: auto;
            }
            .stats-table td { padding: 5px 0; border: none !important; }
            .stats-label { color: #666; font-weight: 500; }
            .stats-value { text-align: right; font-weight: 700; color: #111; }

            .form-wrapper {
                display: flex;
                justify-content: space-between;
                gap: 8px;
                width: 100%;
                margin-top: 15px;
                padding-bottom: 20px;
            }
            .form-column {
                display: flex;
                flex-direction: column;
                align-items: center;
                flex: 1;
            }
            .res-pill {
                width: 100%;
                border-radius: 4px;
                color: white;
                text-align: center;
                font-size: 10px;
                font-weight: 800;
                padding: 4px 0;
                margin-bottom: 6px;
            }
            .legend-logo { width: 26px; height: 26px; object-fit: contain; }
            
            .list-item {
                font-size: 11px;
                margin-bottom: 5px;
                color: #333;
                line-height: 1.2;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
        </style>
    """, unsafe_allow_html=True)

def vis_side(dp=None):
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    DB, LIGA_UUID, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "dyjr458hcmrcy87fsabfsy87o", "8GXD9RY2580PU1B1DD5NY9YMY"
    
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = HIF_UUID.strip().upper()
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.upper()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
    
    col1, col2, col3 = st.columns([1, 1, 1])

    # 1. NÆSTE KAMP
    with col1:
        future = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL')
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['AWAY_ID'] if nk['HOME_ID'] == hif_id else nk['HOME_ID']
                opp_name = opta_to_name.get(opp_id, "Modstander")
                st.markdown(f"<div class='card-title'><span>NÆSTE KAMP vs. {opp_name.upper()}</span><span class='title-date'>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</span></div>", unsafe_allow_html=True)
                
                t_l, t_r = st.columns([1, 1.2])
                with t_l:
                    c1, c2, c3 = st.columns([1, 0.6, 1])
                    c1.image(TEAMS.get("Hvidovre", {}).get("logo", ""), width=42)
                    c2.markdown("<div style='text-align:center; padding-top:12px;'><b style='font-size:10px; color:#ccc;'>VS</b></div>", unsafe_allow_html=True)
                    c3.image(TEAMS.get(opp_name, {}).get("logo", ""), width=42)
                
                with t_r:
                    st.markdown(f"""<table class='stats-table'><tr><td class='stats-label'>Mål f/i</td><td class='stats-value'>1.4/1.1</td></tr><tr><td class='stats-label'>xG f/i</td><td class='stats-value'>1.5/1.2</td></tr><tr><td class='stats-label'>Poss.</td><td class='stats-value'>52%</td></tr></table>""", unsafe_allow_html=True)
                
                st.markdown(f"<div style='font-size:10px; color:#888; font-weight:700; margin-top:14px; text-transform:uppercase;'>Form: {opp_name}</div>", unsafe_allow_html=True)
                opp_m = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & (df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
                if not opp_m.empty:
                    f_items = "".join([f"<div class='form-column'><div class='res-pill' style='background:{('#28a745' if (m['HOME_ID']==opp_id and m['TOTAL_HOME_SCORE']>m['TOTAL_AWAY_SCORE']) or (m['AWAY_ID']==opp_id and m['TOTAL_AWAY_SCORE']>m['TOTAL_HOME_SCORE']) else ('#6c757d' if m['TOTAL_HOME_SCORE']==m['TOTAL_AWAY_SCORE'] else '#dc3545'))};'>{int(m['TOTAL_HOME_SCORE'])}-{int(m['TOTAL_AWAY_SCORE'])}</div><img src='{TEAMS.get(opta_to_name.get(m['AWAY_ID'] if m['HOME_ID']==opp_id else m['HOME_ID'], ''), {}).get('logo', '')}' class='legend-logo'></div>" for _, m in opp_m.iloc[::-1].iterrows()])
                    st.markdown(f"<div class='form-wrapper'>{f_items}</div>", unsafe_allow_html=True)

    # 2. TRANSFERS (Nu med popover der virker)
    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>TRANSFERS</span></div>', unsafe_allow_html=True)
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv")
                # Rens data: Fjern rækker uden timestamp
                df_t = df_t.dropna(subset=['TIMESTAMP'])
                df_t = df_t[df_t['TIMESTAMP'].astype(str).str.strip() != '']
                
                df_t['TS_SORT'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
                df_display = df_t.sort_values('TS_SORT', ascending=False).head(7)
                
                # Vis top 7 i boksen
                for _, r in df_display.iterrows():
                    st.markdown(f"<div class='list-item'><b>{r['KLUB']}</b>: {r['NAVN']}</div>", unsafe_allow_html=True)
                
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                
                # Popover med detaljeret tabel
                with st.popover("Se alle transfers", use_container_width=True):
                    cols_to_show = {
                        'TIMESTAMP': 'Dato',
                        'NAVN': 'Spiller',
                        'FRA_KLUB': 'Fra',
                        'KLUB': 'Til',
                        'KONTRAKT_START': 'Start',
                        'LÆNGDE': 'Længde',
                        'KILDE': 'Kilde'
                    }
                    # Tjekker hvilke kolonner der faktisk findes i din CSV for at undgå fejl
                    existing_cols = {k: v for k, v in cols_to_show.items() if k in df_t.columns}
                    df_final = df_t.sort_values('TS_SORT', ascending=False).rename(columns=existing_cols)
                    st.dataframe(df_final[list(existing_cols.values())], hide_index=True, use_container_width=True)
            except Exception as e:
                st.caption(f"Fejl ved indlæsning: {e}")

    # 3. SCOUTING
    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>SCOUTING</span></div>', unsafe_allow_html=True)
            try:
                df_e = pd.read_csv("data/scouting/emneliste.csv")
                # Viser de senest tilføjede
                for _, r in df_e.tail(7).iloc[::-1].iterrows():
                    st.markdown(f"<div class='list-item'>⭐ {r.get('Navn', 'Ukendt')} ({r.get('Klub', '-')})</div>", unsafe_allow_html=True)
            except:
                st.caption("Scouting-data ikke tilgængelig")

    st.divider()
