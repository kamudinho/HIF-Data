import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONSTANTER & MAPPING ---
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"
EXCLUDE_LIST = ["114516", "570705", "624707", "523647", "39664"] 

# Din opdaterede hold-mapping
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
    """Udtrækker modstandernavn fra kampbeskrivelsen."""
    if not description or ' - ' not in description:
        return "Ukendt"
    teams = [t.strip() for t in description.split(' - ')]
    opp_code = teams[1] if teams[0] == 'HVI' else teams[0]
    return KLUB_NAVNE.get(opp_code, opp_code)

def vis_side(conn, name_map=None):
    # --- 1. SETUP LAYOUT (Dropdown øverst til højre) ---
    header_col, select_col = st.columns([3, 1])
    with header_col:
        st.title("Betinia Ligaen | Fysisk Data")
    
    with select_col:
        alle_hold_navne = sorted(list(TEAMS.keys()))
        default_idx = alle_hold_navne.index("Hvidovre") if "Hvidovre" in alle_hold_navne else 0
        valgt_hold = st.selectbox("Vælg hold", alle_hold_navne, index=default_idx)
        valgt_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. HENT DATA ---
    @st.cache_data(ttl=600)
    def get_raw_data():
        today = datetime.now().strftime('%Y-%m-%d')
        q_meta = f"""
        SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND "DATE" >= '2025-07-01' AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
        """
        q_phys = """
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE >= '2025-07-01'
        """
        return conn.query(q_meta), conn.query(q_phys)

    df_meta, df_phys = get_raw_data()
    
    if df_phys.empty:
        st.error("Ingen fysisk data fundet.")
        return

    # --- 3. DATABEHANDLING (Robust mod optaId fejl) ---
    # Find kolonnen uanset case (optaId / OPTAID)
    col_lookup = {c.lower(): c for c in df_phys.columns}
    db_opta_col = col_lookup.get('optaid', 'optaId')

    def clean_id(x):
        if pd.isna(x) or x == "": return "UKENDT"
        try: return str(int(float(x)))
        except: return str(x).strip()

    df_phys['optaId_str'] = df_phys[db_opta_col].apply(clean_id)
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
    
    def parse_mins(v):
        try:
            if ':' in str(v):
                m, s = map(int, str(v).split(':'))
                return round(m + s/60, 2)
            return float(v or 0)
        except: return 0.0
    
    df_phys['MINS_DEC'] = df_phys['MINUTES'].apply(parse_mins)
    
    # Mapping af klubnavne fra TEAMS config
    opta_to_club = {str(v['opta_id']): k for k, v in TEAMS.items() if 'opta_id' in v}
    df_phys['Klub_Navn'] = df_phys['optaId_str'].map(opta_to_club).fillna("Modstander")
    
    # Mapping af lokale spillernavne
    df_local = load_local_players()
    player_mapping = {}
    if df_local is not None and not df_local.empty:
        loc_col = {c.lower(): c for c in df_local.columns}.get('optaid', 'optaId')
        df_local['oid_clean'] = df_local[loc_col].apply(clean_id)
        player_mapping = df_local.set_index('oid_clean')['NAVN'].to_dict()

    df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: player_mapping.get(r['optaId_str'], r['PLAYER_NAME']), axis=1)
    
    # Fjern ekskluderede spillere
    df_phys = df_phys[~df_phys['optaId_str'].isin(EXCLUDE_LIST)].copy()

    # --- 4. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_hold} Oversigt", "Grafisk", "Top 5 (Liga)", "Kampanalyse"])

    # TAB 1: P90 for valgte hold
    with t1:
        st.subheader(f"Sæsongennemsnit pr. 90 min - {valgt_hold}")
        df_h = df_phys[df_phys['Klub_Navn'] == valgt_hold].copy()
        
        summary = df_h.groupby('DISPLAY_NAME').agg({
            'MINS_DEC': 'sum', 'DISTANCE': 'sum', 'HI_RUN': 'sum', 
            'DISTANCE_TIP': 'sum', 'DISTANCE_OTIP': 'sum', 'TOP_SPEED': 'max'
        }).reset_index()

        summary = summary[summary['MINS_DEC'] > 15].copy()
        summary['KM/90'] = (summary['DISTANCE'] / summary['MINS_DEC']) * 90 / 1000
        summary['HI m/90'] = (summary['HI_RUN'] / summary['MINS_DEC']) * 90
        summary['TIP m/90'] = (summary['DISTANCE_TIP'] / summary['MINS_DEC']) * 90
        summary['OTIP m/90'] = (summary['DISTANCE_OTIP'] / summary['MINS_DEC']) * 90

        st.dataframe(
            summary.sort_values('KM/90', ascending=False),
            column_config={
                "DISPLAY_NAME": "Spiller",
                "KM/90": st.column_config.NumberColumn("KM/90", format="%.2f"),
                "HI m/90": st.column_config.NumberColumn("HI m/90", format="%d"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            column_order=("DISPLAY_NAME", "KM/90", "HI m/90", "TOP_SPEED"),
            use_container_width=True, hide_index=True
        )

    # TAB 2: Grafisk visning
    with t2:
        valg = st.selectbox("Vælg parameter", ["KM/90", "HI m/90", "TOP_SPEED"])
        fig = px.bar(summary.sort_values(valg, ascending=False), x='DISPLAY_NAME', y=valg, 
                     color=valg, color_continuous_scale='Reds', text_auto='.1f')
        fig.update_layout(xaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # TAB 3: Top 5 i ligaen
    with t3:
        st.subheader("Sæsonens højeste enkeltpræstationer (Hele ligaen)")
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.dataframe(df_phys.nlargest(5, 'TOP_SPEED')[['DISPLAY_NAME', 'Klub_Navn', 'TOP_SPEED']], hide_index=True)
        with c2:
            st.write("Højintenst løb (HI m)")
            st.dataframe(df_phys.nlargest(5, 'HI_RUN')[['DISPLAY_NAME', 'Klub_Navn', 'HI_RUN']], hide_index=True)

    # TAB 4: Kampanalyse (Begge hold)
    with t4:
        df_m_list = df_meta[(df_meta['HOME_SSIID'] == valgt_ssid) | (df_meta['AWAY_SSIID'] == valgt_ssid)].copy()
        df_m_list['LABEL'] = df_m_list['DATE'].astype(str) + " - " + df_m_list['DESCRIPTION']
        
        if not df_m_list.empty:
            v_kamp = st.selectbox("Vælg kamp", df_m_list['LABEL'].unique())
            m_id = df_m_list[df_m_list['LABEL'] == v_kamp].iloc[0]['MATCH_SSIID']
            opp_name = get_opponent_name(df_m_list[df_m_list['LABEL'] == v_kamp].iloc[0]['DESCRIPTION'])
            
            df_m_data = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
            df_m_data['KM'] = df_m_data['DISTANCE'] / 1000
            
            # Vis det valgte hold og modstanderen med rigtige navne
            df_m_data['Klub_Visning'] = df_m_data.apply(lambda r: valgt_hold if r['Klub_Navn'] == valgt_hold else opp_name, axis=1)
            
            st.dataframe(
                df_m_data.sort_values(['Klub_Visning', 'DISTANCE'], ascending=[False, False]),
                column_config={"DISPLAY_NAME": "Spiller", "Klub_Visning": "Klub", "KM": st.column_config.NumberColumn("KM", format="%.2f")},
                column_order=("DISPLAY_NAME", "Klub_Visning", "MINUTES", "KM", "HI_RUN", "TOP_SPEED"),
                use_container_width=True, hide_index=True, height=600
            )
