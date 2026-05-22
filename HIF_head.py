import streamlit as st
import pandas as pd
from urllib.parse import urlparse # Til at forkorte links
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn
import datetime
from urllib.parse import urlparse

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
            .stats-table tr, .stats-table td { 
                border: none !important; 
                padding: 4px 0;
            }
            .stats-label { color: #666; font-weight: 500; }
            .stats-value { text-align: right; font-weight: 700; color: #111; }

            .form-wrapper {
                display: flex;
                justify-content: space-between;
                gap: 8px;
                width: 100%;
                margin-top: 20px;
                padding-bottom: 25px; 
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

@st.dialog("Alle Transfers", width="large")
def vis_transfer_dialog(df):
    if df.empty:
        st.write("Ingen data fundet.")
        return

    # Helper til kontrakt-beregning
    def calculate_years(row):
        udloeb = str(row.get('KONTRAKT_UDLOEB', '')).strip()
        start = str(row.get('KONTRAKT_START', '')).strip()
        if udloeb and udloeb != 'nan':
            try:
                dt = pd.to_datetime(udloeb, dayfirst=True, errors='coerce')
                if pd.notnull(dt):
                    # Beregn år fra nu
                    diff = (dt - datetime.datetime.now()).days / 365.25
                    aar = round(max(0, diff))
                    return f"{start} ({aar} år)" if start and start != 'nan' else f"({aar} år)"
            except: pass
        return start if start != 'nan' else "-"

    df_display = df.copy()
    df_display.columns = [str(c).upper().strip() for c in df_display.columns]
    
    # 1. Sortering og Dato
    df_display['TS_SORT'] = pd.to_datetime(df_display['TIMESTAMP'], errors='coerce')
    df_display = df_display.sort_values('TS_SORT', ascending=False)
    df_display['Dato'] = df_display['TS_SORT'].dt.strftime('%d/%m-%Y')
    
    # 2. Spiller (Kun navn)
    df_display['Spiller'] = df_display['NAVN']

    df_display['Position'] = df_display['POSITION']

    # 3. Skifte
    df_display['Skifte'] = df_display['SENESTE_KLUB'].fillna('?') + " ➔ " + df_display['KLUB'].fillna('?')

    # 4. Kontrakt (Beregnet med år)
    df_display['Kontrakt'] = df_display.apply(calculate_years, axis=1)

    # 5. Tabel visning
    st.dataframe(
        df_display,
        column_order=['Dato', 'Spiller', 'Position', 'Skifte', 'Kontrakt', 'KILDE'], 
        column_config={
            "Dato": st.column_config.Column(width="small"),
            "Spiller": st.column_config.Column("Spiller", width="medium"),
            "Position": st.column_config.Column("Position", width="medium"),
            "Skifte": st.column_config.Column("Skifte", width="medium"),
            "Kontrakt": st.column_config.Column("Kontrakt", width="small"),
            "KILDE": st.column_config.LinkColumn("Kilde", display_text="Se kilde"),
        },
        hide_index=True,
        use_container_width=True
    )
    
def vis_side(dp=None):
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    DB, LIGA_UUID, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "dyjr458hcmrcy87fsabfsy87o", "8GXD9RY2580PU1B1DD5NY9YMY"
    
    # (Data load og Næste kamp sektion er uændret...)
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = HIF_UUID.strip().upper()
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == hif_id) | (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == hif_id)].copy()
    
    col1, col2, col3 = st.columns([1, 1, 1])

    # 1. NÆSTE KAMP
    with col1:
        future = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL')
        with st.container(border=True):
            if not opp_m.empty:
                    f_items = ""
                    for _, m in opp_m.iloc[::-1].iterrows():
                        is_h = m['CONTESTANTHOME_OPTAUUID'] == opp_id
                        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                        res_col = "#28a745" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else ("#6c757d" if h_s == a_s else "#dc3545")
                        
                        # Find modstander UUID
                        o_uuid = m['CONTESTANTAWAY_OPTAUUID'] if is_h else m['CONTESTANTHOME_OPTAUUID']
                        
                        # ROBUST HENTNING AF LOGO:
                        # 1. Find navnet fra UUID
                        o_name = opta_to_name.get(o_uuid.upper(), "")
                        # 2. Hent logo fra TEAMS dictionary
                        o_logo = TEAMS.get(o_name, {}).get("logo", "")
                        
                        # Hvis logo mangler, brug en placeholder eller tom string
                        logo_html = f"<img src='{o_logo}' class='legend-logo'>" if o_logo else "<div style='width:26px;'></div>"
                        
                        f_items += f"<div class='form-column'><div class='res-pill' style='background:{res_col};'>{h_s}-{a_s}</div>{logo_html}</div>"
                    
                    st.markdown(f"<div class='form-wrapper'>{f_items}</div>", unsafe_allow_html=True)
                
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
                opp_m = df_matches[((df_matches['CONTESTANTHOME_OPTAUUID'] == opp_id) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == opp_id)) & (df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
                if not opp_m.empty:
                    f_items = ""
                    for _, m in opp_m.iloc[::-1].iterrows():
                        is_h = m['CONTESTANTHOME_OPTAUUID'] == opp_id
                        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                        res_col = "#28a745" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else ("#6c757d" if h_s == a_s else "#dc3545")
                        o_uuid = m['CONTESTANTAWAY_OPTAUUID'] if is_h else m['CONTESTANTHOME_OPTAUUID']
                        o_logo = TEAMS.get(opta_to_name.get(o_uuid.upper(), ""), {}).get("logo", "")
                        f_items += f"<div class='form-column'><div class='res-pill' style='background:{res_col};'>{h_s}-{a_s}</div><img src='{o_logo}' class='legend-logo'></div>"
                    st.markdown(f"<div class='form-wrapper'>{f_items}</div>", unsafe_allow_html=True)

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
                
                # Debug: Tjek kolonnerne i din CSV
                # st.write(df_display.columns) 
                
                for _, r in df_display.iterrows():
                    # 1. Hent rå data
                    dato_raw = r.get('TIMESTAMP', '')
                    klub = str(r.get('KLUB', 'Ukendt'))
                    navn = str(r.get('NAVN', 'Ukendt'))
                    
                    # 2. Hent position - prøv forskellige navne hvis det fejler
                    pos = str(r.get('POSITION', r.get('POS', '-')))
                    
                    # 3. Formater dato sikkert
                    try:
                        dato_str = pd.to_datetime(dato_raw).strftime('%d/%m')
                    except:
                        dato_str = "??/??"

                    st.markdown(f"""
                        <div class='list-item'>
                            {dato_str}: <b>{navn}</b> ({pos}) ➔ <b>{klub}</b>
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
            try:
                df_e = pd.read_csv("data/scouting/emneliste.csv")
                for _, r in df_e.tail(7).iloc[::-1].iterrows():
                    st.markdown(f"<div class='list-item'>⭐ {r.get('Navn', 'Ukendt')} ({r.get('Klub', '-')})</div>", unsafe_allow_html=True)
            except: st.caption("Listen er tom")

    st.divider()
