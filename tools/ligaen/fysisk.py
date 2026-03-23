import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONSTANTER & MAPPING ---
COMP_UUID = "6ifaeunfdelecgticvxanikzu"
EXCLUDE_LIST = ["114516", "570705", "624707", "523647", "39664"] 

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
    # --- 1. LAYOUT & DROPDOWN ---
    header_col, select_col = st.columns([3, 1])
    with header_col:
        st.title("Betinia Ligaen | Fysisk Data")
    with select_col:
        alle_hold = sorted(list(TEAMS.keys()))
        valgt_hold = st.selectbox("Vælg hold", alle_hold, index=alle_hold.index("Hvidovre"))
        valgt_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. HENT DATA ---
    @st.cache_data(ttl=600)
    def get_data():
        today = datetime.now().strftime('%Y-%m-%d')
        q_meta = f"""SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID 
                    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA 
                    WHERE "DATE" >= '2025-07-01' AND "DATE" <= '{today}'"""
        q_phys = """SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS 
                    WHERE MATCH_DATE >= '2025-07-01'"""
        return conn.query(q_meta), conn.query(q_phys)

    df_meta, df_phys = get_data()

    # --- 3. ROBUST DATABEHANDLING ---
    # Case-insensitive kolonne tjek
    cols = {c.lower(): c for c in df_phys.columns}
    opta_col = cols.get('optaid', 'optaId')
    team_ssiid_col = cols.get('teamssiid', 'teamSsiId')

    def clean_id(x):
        if pd.isna(x) or x == "": return "0"
        try: return str(int(float(x)))
        except: return str(x).strip()

    def parse_mins(v):
        if pd.isna(v) or v == "": return 0.0
        try:
            v_s = str(v)
            if ':' in v_s:
                m, s = map(int, v_s.split(':'))
                return round(m + s/60, 2)
            return float(v_s)
        except: return 0.0

    df_phys['optaId_str'] = df_phys[opta_col].apply(clean_id)
    df_phys['MINS_DEC'] = df_phys['MINUTES'].apply(parse_mins)
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
    
    # Lokale navne mapping
    df_local = load_local_players()
    p_map = {}
    if df_local is not None:
        loc_col = {c.lower(): c for c in df_local.columns}.get('optaid', 'optaId')
        df_local['c_oid'] = df_local[loc_col].apply(clean_id)
        p_map = df_local.set_index('c_oid')['NAVN'].to_dict()

    df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: p_map.get(r['optaId_str'], r['PLAYER_NAME']), axis=1)
    df_phys = df_phys[~df_phys['optaId_str'].isin(EXCLUDE_LIST)].copy()

    # --- 4. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_hold} Oversigt", "Grafisk", "Top 5 (Liga)", "Kampanalyse"])

    # TAB 1: FIND ALLE SPILLERE FOR VALGT SSID
    with t1:
        st.subheader(f"Sæsongennemsnit for {valgt_hold}")
        # Vi filtrerer på teamSsiId kolonnen fra Snowflake
        df_valgt = df_phys[df_phys[team_ssiid_col] == valgt_ssid].copy()
        
        summary = df_valgt.groupby('DISPLAY_NAME').agg({
            'MINS_DEC': 'sum', 'DISTANCE': 'sum', 'HI_RUN': 'sum', 'TOP_SPEED': 'max'
        }).reset_index()

        summary = summary[summary['MINS_DEC'] > 15].copy()
        summary['KM/90'] = (summary['DISTANCE'] / summary['MINS_DEC']) * 90 / 1000
        summary['HI m/90'] = (summary['HI_RUN'] / summary['MINS_DEC']) * 90

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

    with t2:
        valg = st.selectbox("Vælg parameter", ["KM/90", "HI m/90", "TOP_SPEED"])
        fig = px.bar(summary.sort_values(valg, ascending=False), x='DISPLAY_NAME', y=valg, 
                     color=valg, color_continuous_scale='Reds', text_auto='.1f')
        fig.update_layout(xaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with t3:
        st.subheader("Sæsonens Top 5 (Alle hold)")
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.dataframe(df_phys.nlargest(5, 'TOP_SPEED')[['DISPLAY_NAME', 'PLAYER_NAME', 'TOP_SPEED']], hide_index=True)
        with c2:
            st.write("HI løb (m)")
            st.dataframe(df_phys.nlargest(5, 'HI_RUN')[['DISPLAY_NAME', 'PLAYER_NAME', 'HI_RUN']], hide_index=True)

    # TAB 4: KAMPANALYSE
    with t4:
        df_kampe = df_meta[(df_meta['HOME_SSIID'] == valgt_ssid) | (df_meta['AWAY_SSIID'] == valgt_ssid)].copy()
        df_kampe['LABEL'] = df_kampe['DATE'].astype(str) + " - " + df_kampe['DESCRIPTION']
        
        if not df_kampe.empty:
            v_label = st.selectbox("Vælg kamp", df_kampe['LABEL'].unique())
            kamp_meta = df_kampe[df_kampe['LABEL'] == v_label].iloc[0]
            m_id = kamp_meta['MATCH_SSIID']
            
            df_m = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
            df_m['KM'] = df_m['DISTANCE'] / 1000
            
            # Identificer hvem der er på det valgte hold
            df_m['Hold_Navn'] = df_m[team_ssiid_col].apply(lambda x: valgt_hold if x == valgt_ssid else "Modstander")
            
            st.dataframe(
                df_m.sort_values(['Hold_Navn', 'DISTANCE'], ascending=[False, False]),
                column_config={"DISPLAY_NAME": "Spiller", "Hold_Navn": "Klub", "KM": st.column_config.NumberColumn("KM", format="%.2f")},
                column_order=("DISPLAY_NAME", "Hold_Navn", "MINUTES", "KM", "HI_RUN", "TOP_SPEED"),
                use_container_width=True, hide_index=True, height=600
            )
