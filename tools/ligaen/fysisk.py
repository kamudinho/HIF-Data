import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONFIGURATION (Præcise 25/26 værdier) ---
SEASON_START = "2025-07-01"

TEAMS = {
    "Hvidovre": {"ssid": "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"},
    "AaB": {"ssid": "40d5387b-ac2f-4e9b-bb97-34456aeb69c4"},
    "Horsens": {"ssid": "f2b45639-d8e6-4d9b-9371-6f9f1fe2a9d9"},
    "Lyngby": {"ssid": "15af1cc2-5ce6-4552-8a5f-7e233a65cedc"},
    "Esbjerg": {"ssid": "bfc8edb9-96af-4152-a8b0-d096d4271f48"},
    "Kolding": {"ssid": "04aaceac-8a20-422b-8417-9199a519c1b3"},
    "HB Køge": {"ssid": "2dccb353-4598-4f35-845d-c6c55c9f5672"},
    "Hillerød": {"ssid": "e274c022-4cf1-4c4d-9555-4c6dd38b1224"},
    "B 93": {"ssid": "e0bb5b5f-2df2-4fc4-854a-e537bd65a280"}
}

def vis_side(conn, name_map=None):
    # --- 1. DROPDOWN ---
    header_col, select_col = st.columns([3, 1])
    with header_col:
        st.title("Betinia Ligaen | Fysisk Data")
    with select_col:
        alle_hold = sorted(list(TEAMS.keys()))
        valgt_hold = st.selectbox("Vælg hold", alle_hold, index=alle_hold.index("Hvidovre"), key="main_team_select")
        v_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. DATA (Kun 2025/2026 sæsonen) ---
    @st.cache_data(ttl=300) # Kortere cache så vi ser opdateringer hurtigt
    def get_phys_data(ssid):
        sql = f"""
        WITH team_player_ids AS (
            SELECT DISTINCT m.MATCH_SSIID, f.value:"optaId"::string AS p_oid
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m,
            LATERAL FLATTEN(input => CASE WHEN m.HOME_SSIID = '{ssid}' THEN m.HOME_PLAYERS ELSE m.AWAY_PLAYERS END) f
            WHERE (m.HOME_SSIID = '{ssid}' OR m.AWAY_SSIID = '{ssid}')
            AND m."DATE" >= '{SEASON_START}'
        )
        SELECT p.*, h.p_oid
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        INNER JOIN team_player_ids h ON p.MATCH_SSIID = h.MATCH_SSIID AND p."optaId" = h.p_oid
        WHERE p.MATCH_DATE >= '{SEASON_START}'
        """
        return conn.query(sql)

    df_phys = get_phys_data(v_ssid)

    # --- 3. DATABEHANDLING ---
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
    
    # Navne-mapping
    df_local = load_local_players()
    p_map = {}
    if df_local is not None:
        df_local['clean_oid'] = df_local['optaId'].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")
        p_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

    df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: p_map.get(str(r['P_OID']), r['PLAYER_NAME']), axis=1)

    # --- 4. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_hold} Sæson", "Grafisk", "Top 5 Liga", "Kampanalyse"])

    with t1:
        summary = df_phys.groupby('DISPLAY_NAME').agg({
            'MINS_DEC': 'sum', 'DISTANCE': 'sum', 'HI_RUN': 'sum', 'TOP_SPEED': 'max'
        }).reset_index()
        summary = summary[summary['MINS_DEC'] > 0]
        summary['KM/90'] = (summary['DISTANCE'] / summary['MINS_DEC'] * 90 / 1000).round(2)
        summary['HI m/90'] = (summary['HI_RUN'] / summary['MINS_DEC'] * 90).astype(int)
        
        st.dataframe(summary.sort_values('KM/90', ascending=False), use_container_width=True, hide_index=True)

    with t4:
        # Hent kun kampe for 25/26 sæsonen for det valgte hold
        df_meta = conn.query(f"""
            SELECT TO_VARCHAR("DATE", 'YYYY-MM-DD') as D, DESCRIPTION, MATCH_SSIID 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA 
            WHERE (HOME_SSIID = '{v_ssid}' OR AWAY_SSIID = '{v_ssid}')
            AND "DATE" >= '{SEASON_START}'
            ORDER BY "DATE" DESC
        """)
        
        if not df_meta.empty:
            df_meta['L'] = df_meta['D'] + " - " + df_meta['DESCRIPTION']
            v_kamp = st.selectbox("Vælg kamp", df_meta['L'].unique(), key="sb_t4")
            m_id = df_meta[df_meta['L'] == v_kamp].iloc[0]['MATCH_SSIID']
            
            # Vis kun spillere fra den valgte kamp
            df_m = conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_SSIID = '{m_id}'")
            df_m['KM'] = (df_m['DISTANCE'] / 1000).round(2)
            
            # Quick check: Er spilleren på det valgte hold?
            # Vi markerer dem baseret på om deres optaId var med i vores sæson-udtræk for det hold
            hold_spillere = df_phys[df_phys['MATCH_SSIID'] == m_id]['P_OID'].tolist()
            df_m['Hold'] = df_m['optaId'].apply(lambda x: valgt_hold if str(x) in hold_spillere else "Modstander")
            
            st.dataframe(df_m.sort_values(['Hold', 'DISTANCE'], ascending=[False, False]), 
                         column_order=("PLAYER_NAME", "Hold", "MINUTES", "KM", "TOP_SPEED"), use_container_width=True, hide_index=True)
