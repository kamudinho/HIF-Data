import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn
import datetime
from data.sql.opta_queries import get_opta_queries

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

    st.dataframe(
        df_display[['Dato', 'Spiller', 'Skifte', 'Kontrakt', 'KILDE']],
        column_config={"KILDE": st.column_config.LinkColumn("Kilde", display_text="Se kilde")},
        hide_index=True, use_container_width=True
    )

def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            .stApp { background-color: #FFFFFF; }
            .card-title { color: #1a1a1a; font-size: 11px; font-weight: 700; margin-bottom: 12px; text-transform: uppercase; border-bottom: 1px solid #f0f0f0; padding-bottom: 6px; display: flex; justify-content: space-between; }
            
            /* FORMKURVE JUSTERINGER */
            .form-wrapper { display: flex; justify-content: space-between; gap: 4px; width: 100%; margin-top: 12px; padding-bottom: 10px; }
            .form-column { display: flex; flex-direction: column; align-items: center; flex: 1; }
            .res-pill { width: 100%; border-radius: 4px; color: white; text-align: center; font-size: 9px; font-weight: 800; padding: 2px 0; margin-bottom: 4px; }
            .legend-logo { width: 20px; height: 20px; object-fit: contain; }
            
            /* KNAP JUSTERINGER */
            div.stButton > button { 
                padding: 1px 6px !important; 
                font-size: 9px !important; 
                height: 12px !important; 
                width: auto !important; 
                margin-top: 4px !important;
                border-radius: 3px !important;
            }
            
            /* Grid layout til transfers */
            .list-item { font-size: 10px; margin-bottom: 6px; color: #333; display: grid; grid-template-columns: 1fr auto auto auto; align-items: center; gap: 4px; width: 100%; }
            .prev-club { color: #aaa; font-size: 9px; text-align: right; }
            .new-club { font-weight: 700; text-align: right; }
            .stats-table { width: 100%; border-collapse: collapse; }
            .stats-label { color: #888; padding-right: 10px; }
            .stats-value { font-weight: 700; text-align: right; }
       </style>
    """, unsafe_allow_html=True)

def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    DB, LIGA_UUID, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "dyjr458hcmrcy87fsabfsy87o", "8GXD9RY2580PU1B1DD5NY9YMY"

    # Hent data
    df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    df_matches.columns = [str(c).upper() for c in df_matches.columns]

    queries = get_opta_queries(liga_f="NordicBet Liga", saeson_f="2025/2026", hif_only=True)
    df_team = conn.query(queries["opta_team_stats"])
    
    # Datarensning for at undgå float NaN fejl
    for col in ['TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE']:
        if col in df_team.columns:
            df_team[col] = pd.to_numeric(df_team[col], errors='coerce').fillna(0).astype(int)

    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        with st.container(border=True):
            # 1. Konverter datoen først så sortering virker
            df_matches['MATCH_DATE_DT'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
            
            # 2. Filtrer kampe der IKKE er spillet (og sørg for at de har en dato)
            future = df_matches[
                ~df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish|postponed|abandoned', na=False) & 
                df_matches['MATCH_DATE_DT'].notnull()
            ].sort_values('MATCH_DATE_DT', ascending=True) # Sorter stigende så den tidligste fremtidige kamp er først
            
            if not future.empty:
                nk = future.iloc[0]
                # Logik for at finde modstanderen
                opp_id = nk['CONTESTANTAWAY_OPTAUUID'] if str(nk['CONTESTANTHOME_OPTAUUID']).upper() == HIF_UUID.strip().upper() else nk['CONTESTANTHOME_OPTAUUID']
                opp_name = opta_to_name.get(str(opp_id).upper(), "Ukendt")
                is_home = df_team['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID.strip().upper()
                avg_goals_f = round(pd.concat([df_team.loc[is_home, 'TOTAL_HOME_SCORE'], df_team.loc[~is_home, 'TOTAL_AWAY_SCORE']]).mean(), 1)
                avg_goals_i = round(pd.concat([df_team.loc[is_home, 'TOTAL_AWAY_SCORE'], df_team.loc[~is_home, 'TOTAL_HOME_SCORE']]).mean(), 1)

                st.markdown(f"<div class='card-title'><span>NÆSTE KAMP vs. {opp_name.upper()}</span></div>", unsafe_allow_html=True)

                t_l, t_r = st.columns([1, 1.2]) 
                with t_l:
                    c1, c2, c3 = st.columns([1, 0.8, 1]) 
                    c1.image(TEAMS.get("Hvidovre", {}).get("logo", ""), width=38)
                    c2.markdown("<div style='text-align:center; padding-top:10px; font-size:9px; color:#888;'>VS</div>", unsafe_allow_html=True)
                    c3.image(TEAMS.get(opp_name, {}).get("logo", ""), width=38)

                with t_r:
                    st.markdown(f"""
                        <table class='stats-table' style='font-size: 10px;'>
                            <tr><td class='stats-label'>Mål f/i</td><td class='stats-value'>{avg_goals_f}/{avg_goals_i}</td></tr>
                            <tr><td class='stats-label'>Form</td><td class='stats-value'>Sidste 5</td></tr>
                        </table>
                    """, unsafe_allow_html=True)

                f_items = ""
                for _, m in df_team.head(5).iloc[::-1].iterrows():
                    is_h = str(m['CONTESTANTHOME_OPTAUUID']).upper() == HIF_UUID.strip().upper()
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
