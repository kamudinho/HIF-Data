import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONFIGURATION ---
TEAMS = {
    "Hvidovre": {"opta_id": 2397, "ssid": "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"},
    "AaB": {"opta_id": 401, "ssid": "40d5387b-ac2f-4e9b-bb97-34456aeb69c4"},
    "Horsens": {"opta_id": 2289, "ssid": "f2b45639-d8e6-4d9b-9371-6f9f1fe2a9d9"},
    "Lyngby": {"opta_id": 272, "ssid": "15af1cc2-5ce6-4552-8a5f-7e233a65cedc"},
    "Esbjerg": {"opta_id": 1409, "ssid": "bfc8edb9-96af-4152-a8b0-d096d4271f48"},
    "Kolding": {"opta_id": 13253, "ssid": "04aaceac-8a20-422b-8417-9199a519c1b3"},
    "Hobro": {"opta_id": 4802, "ssid": "e274c022-4cf1-4c4d-9555-4c6dd38b1224"},
    "HB Køge": {"opta_id": 4042, "ssid": "2dccb353-4598-4f35-845d-c6c55c9f5672"},
    "Hillerød": {"opta_id": 6463, "ssid": "e274c022-4cf1-4c4d-9555-4c6dd38b1224"},
    "Aarhus Fremad": {"opta_id": 2290, "ssid": "cd08baf0-84c3-490a-9879-da4a55b8e645"},
    "B 93": {"opta_id": 2935, "ssid": "e0bb5b5f-2df2-4fc4-854a-e537bd65a280"},
    "Middelfart": {"opta_id": 3050, "ssid": "3a0f347e-1ebc-4a89-97dc-a12caaadeaf2"}
}

def vis_side(conn, name_map=None):
    # --- 1. DROPDOWN ---
    header_col, select_col = st.columns([3, 1])
    with header_col:
        st.title("Betinia Ligaen | Fysisk Data")
    with select_col:
        alle_hold = sorted(list(TEAMS.keys()))
        valgt_hold = st.selectbox("Vælg hold", alle_hold, index=alle_hold.index("Esbjerg") if "Esbjerg" in alle_hold else 0)
        valgt_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. DATA ---
    @st.cache_data(ttl=600)
    def get_data():
        today = datetime.now().strftime('%Y-%m-%d')
        q_meta = f'SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA WHERE "DATE" >= \'2025-07-01\' AND "DATE" <= \'{today}\''
        q_phys = 'SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_DATE >= \'2025-07-01\''
        return conn.query(q_meta), conn.query(q_phys)

    df_meta, df_phys = get_data()

    # --- 3. KOLONNE DETEKTOR (Løser 'optaId' fejlen) ---
    cols = {c.lower(): c for c in df_phys.columns}
    c_opta = cols.get('optaid', 'optaId')
    c_match = cols.get('match_ssiid', 'MATCH_SSIID')

    # --- 4. DATABEHANDLING ---
    def parse_mins(v):
        if pd.isna(v) or v == "": return 0.0
        try:
            v_s = str(v)
            if ':' in v_s:
                m, s = map(int, v_s.split(':'))
                return round(m + s/60, 2)
            return float(v_s)
        except: return 0.0

    df_phys['MINS_DEC'] = df_phys['MINUTES'].apply(parse_mins)
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
    df_phys['optaId_str'] = df_phys[c_opta].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")

    # Klub mapping
    opta_to_club = {str(v['opta_id']): k for k, v in TEAMS.items()}
    df_phys['KLUB_NAVN'] = df_phys['optaId_str'].map(opta_to_club).fillna("Modstander")

    # Navne fra Excel
    df_local = load_local_players()
    p_map = {}
    if df_local is not None:
        l_cols = {c.lower(): c for c in df_local.columns}
        l_opta = l_cols.get('optaid', 'optaId')
        df_local['clean_oid'] = df_local[l_opta].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")
        p_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

    df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: p_map.get(r['optaId_str'], r['PLAYER_NAME']), axis=1)

    # --- 5. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_hold} Oversigt", "Grafisk", "Top 5 (Liga)", "Kampanalyse"])

    # T1: Oversigt
    df_team = df_phys[df_phys['KLUB_NAVN'] == valgt_hold].copy()
    summary = df_team.groupby('DISPLAY_NAME').agg({
        'MINS_DEC': 'sum', 'DISTANCE': 'sum', 'HI_RUN': 'sum', 'TOP_SPEED': 'max'
    }).reset_index()
    
    if not summary.empty:
        summary = summary[summary['MINS_DEC'] > 5].copy()
        summary['KM/90'] = (summary['DISTANCE'] / summary['MINS_DEC']) * 90 / 1000
        summary['HI m/90'] = (summary['HI_RUN'] / summary['MINS_DEC']) * 90

    with t1:
        st.subheader(f"Gennemsnit pr. 90 min: {valgt_hold}")
        st.dataframe(summary.sort_values('KM/90', ascending=False), use_container_width=True, hide_index=True)

    with t2:
        valg = st.selectbox("Vælg parameter", ["KM/90", "HI m/90", "TOP_SPEED"])
        fig = px.bar(summary.sort_values(valg, ascending=False), x='DISPLAY_NAME', y=valg, color_discrete_sequence=['red'])
        st.plotly_chart(fig, use_container_width=True)

    with t3:
        st.subheader("Ligaens Top 5")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Topfart**")
            st.dataframe(df_phys.sort_values('TOP_SPEED', ascending=False).drop_duplicates('DISPLAY_NAME').head(5)[['DISPLAY_NAME', 'KLUB_NAVN', 'TOP_SPEED']], hide_index=True)
        with col2:
            st.write("**HI Meter (Enkelt kamp)**")
            st.dataframe(df_phys.nlargest(5, 'HI_RUN')[['DISPLAY_NAME', 'KLUB_NAVN', 'HI_RUN']], hide_index=True)

    with t4:
        df_kampe = df_meta[(df_meta['HOME_SSIID'] == valgt_ssid) | (df_meta['AWAY_SSIID'] == valgt_ssid)].copy()
        df_kampe['LABEL'] = df_kampe['DATE'].astype(str) + " - " + df_kampe['DESCRIPTION']
        
        if not df_kampe.empty:
            v_kamp = st.selectbox("Vælg kamp", df_kampe['LABEL'].unique())
            m_id = df_kampe[df_kampe['LABEL'] == v_kamp].iloc[0]['MATCH_SSIID']
            df_m = df_phys[df_phys[c_match] == m_id].copy()
            df_m['KM'] = df_m['DISTANCE'] / 1000
            df_m['Hold'] = df_m['KLUB_NAVN'].apply(lambda x: valgt_hold if x == valgt_hold else "Modstander")
            st.dataframe(df_m.sort_values(['Hold', 'DISTANCE'], ascending=[False, False]), 
                         column_order=("DISPLAY_NAME", "Hold", "MINUTES", "KM", "HI_RUN", "TOP_SPEED"), use_container_width=True, hide_index=True)
