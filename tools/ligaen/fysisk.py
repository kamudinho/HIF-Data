import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players

# --- KONSTANTER & MAPPING (Brug din TEAMS fra tidligere) ---
# Jeg har inkluderet den her for overskuelighed
TEAMS = {
    "Hvidovre": {"opta_id": 2397, "ssid": "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"},
    "AaB": {"opta_id": 401, "ssid": "40d5387b-ac2f-4e9b-bb97-34456aeb69c4"},
    "Horsens": {"opta_id": 2289, "ssid": "f2b45639-d8e6-4d9b-9371-6f9f1fe2a9d9"},
    "Lyngby": {"opta_id": 272, "ssid": "15af1cc2-5ce6-4552-8a5f-7e233a65cedc"},
    "B 93": {"opta_id": 2935, "ssid": "e0bb5b5f-2df2-4fc4-854a-e537bd65a280"},
    # ... tilføj resten af dine hold her
}

def vis_side(conn, name_map=None):
    # --- 1. DROPDOWN TIL HOLDVALG ---
    st.sidebar.markdown("---")
    alle_hold_navne = sorted(list(TEAMS.keys()))
    valgt_hold = st.sidebar.selectbox("Vælg hold til analyse", alle_hold_navne, index=alle_hold_navne.index("Hvidovre"))
    valgt_hold_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. HENT DATA ---
    @st.cache_data(ttl=600)
    def get_data():
        today = datetime.now().strftime('%Y-%m-%d')
        # Metadata for alle kampe (så vi kan finde modstandere)
        q_meta = f"""SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID 
                    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA 
                    WHERE "DATE" >= '2025-07-01' AND "DATE" <= '{today}'"""
        # Alt fysisk data
        q_phys = """SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS 
                    WHERE MATCH_DATE >= '2025-07-01'"""
        return conn.query(q_meta), conn.query(q_phys)

    df_meta, df_phys = get_data()

    # --- 3. ROBUST DATABEHANDLING (LØSNING PÅ optaId FEJL) ---
    # Find den rigtige kolonne uanset case (optaId vs OPTAID)
    col_map = {c.lower(): c for c in df_phys.columns}
    opta_col = col_map.get('optaid', 'optaId') 
    
    def clean_id(x):
        if pd.isna(x) or x == "": return "0"
        try: return str(int(float(x)))
        except: return str(x).strip()

    df_phys['optaId_str'] = df_phys[opta_col].apply(clean_id)
    
    # Mapping tabeller
    opta_to_club = {str(v['opta_id']): k for k, v in TEAMS.items()}
    df_local = load_local_players()
    player_map = {}
    if df_local is not None:
        # Samme fix for din Excel fil
        loc_cols = {c.lower(): c for c in df_local.columns}
        loc_opta = loc_cols.get('optaid', 'optaId')
        df_local['clean_oid'] = df_local[loc_opta].apply(clean_id)
        player_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

    # Tilføj Navn og Klub (Sandgrav fix)
    df_phys['NAVN_FIX'] = df_phys.apply(lambda r: player_map.get(r['optaId_str'], r['PLAYER_NAME']), axis=1)
    df_phys['KLUB_FIX'] = df_phys['optaId_str'].map(opta_to_club).fillna("Anden")

    # Beregnings-kolonner
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
    def to_mins(v):
        try:
            if ':' in str(v):
                m, s = map(int, str(v).split(':'))
                return round(m + s/60, 2)
            return float(v or 0)
        except: return 0.0
    df_phys['MINS'] = df_phys['MINUTES'].apply(to_mins)

    # --- 4. VISNING (TABS) ---
    t1, t3 = st.tabs(["Holdoversigt", "Kampanalyse"])

    with t1:
        st.subheader(f"Fysiske stats: {valgt_hold}")
        df_h = df_phys[df_phys['KLUB_FIX'] == valgt_hold].copy()
        summary = df_h.groupby('NAVN_FIX').agg({
            'MINS': 'sum', 'DISTANCE': 'sum', 'HI_RUN': 'sum', 'TOP_SPEED': 'max'
        }).reset_index()
        
        # P90 beregning
        summary = summary[summary['MINS'] > 10]
        summary['KM/90'] = (summary['DISTANCE'] / summary['MINS']) * 90 / 1000
        
        st.dataframe(summary.sort_values('KM/90', ascending=False), use_container_width=True, hide_index=True)
        
        # Graf for valgte hold
        fig = px.bar(summary, x='NAVN_FIX', y='KM/90', title=f"Distance pr. 90 min - {valgt_hold}", color_discrete_sequence=['#cc0000'])
        st.plotly_chart(fig, use_container_width=True)

    with t3:
        # Find kampe for det valgte hold
        df_m_list = df_meta[(df_meta['HOME_SSIID'] == valgt_hold_ssid) | (df_meta['AWAY_SSIID'] == valgt_hold_ssid)].copy()
        df_m_list['LABEL'] = df_m_list['DATE'].astype(str) + " - " + df_m_list['DESCRIPTION']
        
        if not df_m_list.empty:
            valgt_m = st.selectbox("Vælg kamp", df_m_list['LABEL'].unique())
            m_id = df_m_list[df_m_list['LABEL'] == valgt_m].iloc[0]['MATCH_SSIID']
            
            df_m_data = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
            df_m_data['KM'] = df_m_data['DISTANCE'] / 1000
            
            st.write(f"Data for begge hold i kampen: {valgt_m}")
            st.dataframe(
                df_m_data.sort_values(['KLUB_FIX', 'DISTANCE'], ascending=[True, False]),
                column_order=("NAVN_FIX", "KLUB_FIX", "MINUTES", "KM", "HI_RUN", "TOP_SPEED"),
                use_container_width=True, hide_index=True
            )
