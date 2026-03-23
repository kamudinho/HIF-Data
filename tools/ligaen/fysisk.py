import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONSTANTER & MAPPING ---
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"
EXCLUDE_LIST = ["114516", "570705", "624707", "523647", "39664"] 

# Din centraliserede hold-mapping
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

KLUB_NAVNE = {
    "HVI": "Hvidovre IF", "KIF": "Kolding IF", "MID": "Middelfart",
    "HIK": "Hobro IK", "LBK": "Lyngby BK", "B93": "B.93",
    "ARF": "Aarhus Fremad", "ACH": "Horsens", "HBK": "HB Køge",
    "EFB": "Esbjerg fB", "HIL": "Hillerød", "AAB": "AaB"
}

def get_opponent_name(description):
    if not description or ' - ' not in description:
        return "Ukendt"
    teams = [t.strip() for t in description.split(' - ')]
    opp_code = teams[1] if teams[0] == 'HVI' else teams[0]
    return KLUB_NAVNE.get(opp_code, opp_code)

def vis_side(conn, name_map=None):
    # --- 1. SETUP & MAPPING ---
    df_local = load_local_players()
    player_mapping = {}
    if df_local is not None and not df_local.empty:
        df_local['optaId_clean'] = df_local['optaId'].apply(
            lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','',1).isdigit() else str(x)
        )
        player_mapping = df_local.set_index('optaId_clean')['NAVN'].to_dict()

    # --- 2. DYNAMISK HOLDVALG ---
    # Vi henter alle unikke holdnavne fra din TEAMS konfiguration
    alle_hold = sorted(list(TEAMS.keys()))
    valgt_oversigt_hold = st.sidebar.selectbox("Vælg hold til oversigt", alle_hold, index=alle_hold.index("Hvidovre"))
    valgt_ssid = TEAMS[valgt_oversigt_hold]["ssid"]

    # --- 3. HENT DATA (NU MERE GENERELT) ---
    @st.cache_data(ttl=600)
    def get_safe_data():
        today = datetime.now().strftime('%Y-%m-%d')
        # Henter metadata for alle kampe i divisionen
        query_meta = f"""
        SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND "DATE" >= '2025-07-01' AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
        """
        # Henter fysisk data for alle spillere
        query_phys = f"""
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE >= '2025-07-01'
        """
        return conn.query(query_meta), conn.query(query_phys)

    df_meta, df_phys = get_safe_data()

    # --- 4. DATABEHANDLING ---
    opta_to_club = {str(v['opta_id']): k for k, v in TEAMS.items() if 'opta_id' in v}
    
    def clean_id(x):
        try: return str(int(float(x)))
        except: return str(x).strip()

    df_phys['optaId_str'] = df_phys['optaId'].apply(clean_id)
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
    df_phys['MINS_DECIMAL'] = df_phys['MINUTES'].apply(lambda x: round(int(str(x).split(':')[0]) + int(str(x).split(':')[1])/60, 2) if ':' in str(x) else float(x or 0))
    
    # Map Navne og Korrekt Klub
    df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: player_mapping.get(r['optaId_str'], r['PLAYER_NAME']), axis=1)
    
    def get_assigned_club(row):
        oid = row['optaId_str']
        return opta_to_club.get(oid, "Ukendt")

    df_phys['Klub_Korrekt'] = df_phys.apply(get_assigned_club, axis=1)
    df_phys = df_phys[~df_phys['optaId_str'].isin(EXCLUDE_LIST)].copy()

    # --- 5. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_oversigt_hold} P90", "Grafisk Visning", "Top 5 (Hele Ligaen)", "Kampanalyse"])

    # TAB 1 & 2: Filtreret på det valgte hold fra dropdown
    with t1:
        st.subheader(f"Gennemsnit for {valgt_oversigt_hold}")
        df_valgt = df_phys[df_phys['Klub_Korrekt'] == valgt_oversigt_hold].copy()
        
        summary = df_valgt.groupby('DISPLAY_NAME').agg({
            'MINS_DECIMAL': 'sum', 'DISTANCE': 'sum', 'HI_RUN': 'sum', 
            'DISTANCE_TIP': 'sum', 'DISTANCE_OTIP': 'sum', 'TOP_SPEED': 'max'
        }).reset_index()
        
        summary = summary[summary['MINS_DECIMAL'] > 15].copy()
        # Beregninger... (KM/90, HI m/90 osv.)
        summary['KM/90'] = (summary['DISTANCE'] / summary['MINS_DECIMAL']) * 90 / 1000
        summary['HI m/90'] = (summary['HI_RUN'] / summary['MINS_DECIMAL']) * 90

        st.dataframe(summary.sort_values('KM/90', ascending=False), use_container_width=True, hide_index=True)

    with t2:
        valg = st.selectbox("Vælg parameter", ["KM/90", "HI m/90", "TOP_SPEED"])
        fig = px.bar(summary.sort_values(valg, ascending=False), x='DISPLAY_NAME', y=valg, color=valg, color_continuous_scale='reds')
        st.plotly_chart(fig, use_container_width=True)

    # TAB 4: KAMPANALYSE (Viser alle spillere i den valgte kamp)
    with t4:
        # Find kampe hvor det valgte hold har deltaget
        df_kampe = df_meta[(df_meta['HOME_SSIID'] == valgt_ssid) | (df_meta['AWAY_SSIID'] == valgt_ssid)].copy()
        df_kampe['LABEL'] = df_kampe['DATE'].astype(str) + " - " + df_kampe['DESCRIPTION']
        
        if not df_kampe.empty:
            valgt_kamp_label = st.selectbox("Vælg kamp", df_kampe['LABEL'].unique())
            kamp_id = df_kampe[df_kampe['LABEL'] == valgt_kamp_label].iloc[0]['MATCH_SSIID']
            
            df_kamp_data = df_phys[df_phys['MATCH_SSIID'] == kamp_id].copy()
            df_kamp_data['KM'] = df_kamp_data['DISTANCE'] / 1000
            
            # Vi sorterer så det valgte hold ligger øverst
            df_kamp_data['Sort_Order'] = df_kamp_data['Klub_Korrekt'].apply(lambda x: 0 if x == valgt_oversigt_hold else 1)
            
            st.dataframe(
                df_kamp_data.sort_values(['Sort_Order', 'DISTANCE'], ascending=[True, False]),
                column_order=("DISPLAY_NAME", "Klub_Korrekt", "MINUTES", "KM", "HI_RUN", "TOP_SPEED"),
                use_container_width=True, hide_index=True
            )
