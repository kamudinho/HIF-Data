import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn
import datetime

# --- DIALOG-BOKS (Skal defineres øverst) ---
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
            .card-title { color: #1a1a1a; font-size: 11px; font-weight: 700; margin-bottom: 15px; text-transform: uppercase; border-bottom: 1px solid #f0f0f0; padding-bottom: 8px; display: flex; justify-content: space-between; }
            .title-date { color: #888; font-weight: 500; text-transform: none; font-size: 11px; }
            .stats-table { width: 100%; font-size: 10px; border-collapse: collapse; table-layout: fixed; }
            .stats-label { color: #666; font-weight: 700; width: 40%; }
            .stats-value { text-align: right; font-weight: 700; color: #111; padding: 4px 0; }
            .form-wrapper { display: flex; justify-content: space-between; gap: 4px; width: 100%; margin-top: 15px; }
            .form-column { display: flex; flex-direction: column; align-items: center; flex: 1; }
            .res-pill { width: 100%; border-radius: 4px; color: white; text-align: center; font-size: 10px; font-weight: 800; padding: 4px 0; margin-bottom: 6px; }
            .legend-logo { width: 26px; height: 26px; object-fit: contain; }
            
            /* Det nye GRID layout til transfers */
            .list-item { 
                font-size: 11px; 
                margin-bottom: 6px; 
                color: #333; 
                display: grid;
                grid-template-columns: 1fr auto auto auto; 
                align-items: center;
                gap: 6px;
                width: 100%;
            }
            .prev-club { color: #aaa; font-size: 10px; text-align: right; }
            .new-club { font-weight: 700; text-align: right; }
        </style>
    """, unsafe_allow_html=True)

div.stButton > button {
    padding: 2px 10px !important;
    font-size: 11px !important;
    height: auto !important;
    min-height: 25px !important;
    margin-top: 5px;
}
    
def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return

    DB, LIGA_UUID, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "dyjr458hcmrcy87fsabfsy87o", "8GXD9RY2580PU1B1DD5NY9YMY"
    df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    col1, col2, col3 = st.columns([1, 1, 1])

    # 1. COL1: Næste kamp, Metrics, Legends
    with col1:
        with st.container(border=True):
            hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.upper() == HIF_UUID.strip().upper()) | (df_matches['CONTESTANTAWAY_OPTAUUID'].str.upper() == HIF_UUID.strip().upper())]
            future = hif_m[~hif_m['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL')
            
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['CONTESTANTAWAY_OPTAUUID'] if str(nk['CONTESTANTHOME_OPTAUUID']).upper() == HIF_UUID.strip().upper() else nk['CONTESTANTHOME_OPTAUUID']
                opp_name = opta_to_name.get(str(opp_id).upper(), "Ukendt")
                
                st.markdown(f"<div class='card-title'><span>NÆSTE KAMP vs. {opp_name.upper()}</span><span class='title-date'>{nk['MATCH_DATE_FULL'].strftime('%d/%m')}</span></div>", unsafe_allow_html=True)
                
                t_l, t_r = st.columns([1, 1.5])
                with t_l:
                    c1, c2, c3 = st.columns([1, 0.5, 1])
                    c1.image(TEAMS.get("Hvidovre", {}).get("logo", ""), width=42)
                    c2.markdown("<div style='text-align:center; padding-top:10px;'>VS</div>", unsafe_allow_html=True)
                    c3.image(TEAMS.get(opp_name, {}).get("logo", ""), width=42)
                with t_r:
                    st.markdown(f"<table class='stats-table'><tr><td class='stats-label'>Mål f/i</td><td class='stats-value'>1.4/1.1</td></tr><tr><td class='stats-label'>xG f/i</td><td class='stats-value'>1.5/1.2</td></tr><tr><td class='stats-label'>Poss.</td><td class='stats-value'>52%</td></tr></table>", unsafe_allow_html=True)
                
                # Legends
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

    # 2. COL2: Transfers med højrejusterede klubnavne
    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>TRANSFERS</span></div>', unsafe_allow_html=True)
            try:
                df_t = pd.read_csv("data/players/1div_overskrivning.csv")
                df_t['TS_DATE'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
                df_t = df_t.dropna(subset=['TS_DATE'])
                
                for _, r in df_t.sort_values('TS_DATE', ascending=False).head(5).iterrows():
                    dato_str = r['TS_DATE'].strftime('%d/%m')
                    
                    # Hent klubnavne (brug '?' hvis de mangler i CSV)
                    fra_klub = r.get('SENESTE_KLUB', '?')
                    til_klub = r.get('KLUB', '?')
                    
                    st.markdown(f"""
                        <div class='list-item'>
                            <span>{dato_str}: <b>{r['NAVN']}</b> ({r['POSITION']})</span>
                            <span class='prev-club'>{fra_klub}</span>
                            <span class='transfer-club'>➔ {til_klub}</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                if st.button("Se alle transfers", key="transfers_btn", use_container_width=True):
                    vis_transfer_dialog(df_t)
            except Exception as e:
                st.caption("Kunne ikke indlæse transfer-data")
    # 3. COL3: Scouting
    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title"><span>SCOUTING</span></div>', unsafe_allow_html=True)
