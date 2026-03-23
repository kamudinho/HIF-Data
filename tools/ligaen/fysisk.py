import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONFIGURATION ---
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
    # --- 1. LAYOUT & DYNAMISK DROPDOWN ---
    header_col, select_col = st.columns([3, 1])
    with header_col:
        st.title("Betinia Ligaen | Fysisk Data")
    
    with select_col:
        alle_hold = sorted(list(TEAMS.keys()))
        # Finder index for Hvidovre som standard, ellers 0
        hvi_idx = alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0
        valgt_hold = st.selectbox("Vælg hold", alle_hold, index=hvi_idx)
        valgt_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. DATA INDLÆSNING ---
    @st.cache_data(ttl=600)
    def get_data():
        today = datetime.now().strftime('%Y-%m-%d')
        # Metadata til kampvalg
        q_meta = f"""SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID 
                    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA 
                    WHERE "DATE" >= '2025-07-01' AND "DATE" <= '{today}'"""
        # Fysisk data for alle spillere
        q_phys = """SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS 
                    WHERE MATCH_DATE >= '2025-07-01'"""
        return conn.query(q_meta), conn.query(q_phys)

    df_meta, df_phys = get_data()

    if df_phys.empty:
        st.warning("Ingen data fundet i databasen.")
        return

    # --- 3. ROBUST DATABEHANDLING ---
    # Case-insensitive kolonne-identifikation (Snowflake UPPERCASE fix)
    cols = {c.lower(): c for c in df_phys.columns}
    opta_col = cols.get('optaid', 'optaId')
    team_ssiid_col = cols.get('teamssiid', 'TEAM_SSID')

    # Fix for minut-format og float-fejl
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
    
    # Navne-mapping fra lokal Excel (hvis den findes)
    df_local = load_local_players()
    p_map = {}
    if df_local is not None and not df_local.empty:
        loc_col = {c.lower(): c for c in df_local.columns}.get('optaid', 'optaId')
        df_local['clean_oid'] = df_local[loc_col].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")
        p_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

    # Funktion til at hente pænt navn eller fallback til PLAYER_NAME
    def get_display_name(row):
        try:
            oid = str(int(float(row[opta_col]))) if pd.notnull(row[opta_col]) else "0"
            return p_map.get(oid, row['PLAYER_NAME'])
        except:
            return row['PLAYER_NAME']

    df_phys['DISPLAY_NAME'] = df_phys.apply(get_display_name, axis=1)
    
    # Ekskluder test-id'er eller uønskede rækker
    df_phys = df_phys[~df_phys[opta_col].astype(str).isin(EXCLUDE_LIST)].copy()

    # --- 4. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_hold} Oversigt", "Grafisk Visning", "Top 5 (Liga)", "Kampanalyse"])

    # TAB 1: SÆSON-OVERSIGT FOR VALGTE HOLD (Baseret på TEAM_SSIID)
    with t1:
        st.subheader(f"Sæsongennemsnit pr. 90 min: {valgt_hold}")
        # Filtrerer alt data så vi kun ser spillere for det valgte holds SSID
        df_team = df_phys[df_phys[team_ssiid_col] == valgt_ssid].copy()
        
        summary = df_team.groupby('DISPLAY_NAME').agg({
            'MINS_DEC': 'sum', 'DISTANCE': 'sum', 'HI_RUN': 'sum', 'TOP_SPEED': 'max'
        }).reset_index()

        summary = summary[summary['MINS_DEC'] > 15].copy() # Kun spillere med minutter
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

    # TAB 2: GRAFISK VISNING
    with t2:
        valg = st.selectbox("Vælg parameter til graf", ["KM/90", "HI m/90", "TOP_SPEED"])
        fig = px.bar(summary.sort_values(valg, ascending=False), x='DISPLAY_NAME', y=valg, 
                     color=valg, color_continuous_scale='Reds', text_auto='.1f')
        fig.update_layout(xaxis_title=None, yaxis_title=valg, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    # TAB 3: TOP 5 I LIGAEN
    with t3:
        st.subheader("Sæsonens højeste præstationer (Hele ligaen)")
        col_l, col_r = st.columns(2)
        with col_l:
            st.write("**Højeste Topfart (km/t)**")
            st.dataframe(df_phys.nlargest(5, 'TOP_SPEED')[['DISPLAY_NAME', 'PLAYER_NAME', 'TOP_SPEED']], hide_index=True)
        with col_r:
            st.write("**Mest Højintenst Løb (meter)**")
            st.dataframe(df_phys.nlargest(5, 'HI_RUN')[['DISPLAY_NAME', 'PLAYER_NAME', 'HI_RUN']], hide_index=True)

    # TAB 4: KAMPANALYSE (VISER BEGGE HOLD)
    with t4:
        # Find kampe hvor det valgte hold deltog (uanset ude/hjemme)
        df_kampe_valgt = df_meta[(df_meta['HOME_SSIID'] == valgt_ssid) | (df_meta['AWAY_SSIID'] == valgt_ssid)].copy()
        df_kampe_valgt['LABEL'] = df_kampe_valgt['DATE'].astype(str) + " - " + df_kampe_valgt['DESCRIPTION']
        
        if not df_kampe_valgt.empty:
            valgt_kamp = st.selectbox("Vælg kamp fra listen", df_kampe_valgt['LABEL'].unique())
            m_id = df_kampe_valgt[df_kampe_valgt['LABEL'] == valgt_kamp].iloc[0]['MATCH_SSIID']
            
            df_m = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
            df_m['KM'] = df_m['DISTANCE'] / 1000
            
            # Identificer hvem der spiller for dit valgte hold via teamSsiId
            df_m['Hold'] = df_m[team_ssiid_col].apply(lambda x: valgt_hold if x == valgt_ssid else "Modstander")
            
            # Sorterer så dit hold står øverst, og derefter på løbet distance
            df_m['Sort_Order'] = df_m['Hold'].apply(lambda x: 0 if x == valgt_hold else 1)
            
            st.dataframe(
                df_m.sort_values(['Sort_Order', 'DISTANCE'], ascending=[True, False]),
                column_config={
                    "DISPLAY_NAME": "Spiller",
                    "Hold": "Klub",
                    "KM": st.column_config.NumberColumn("KM", format="%.2f")
                },
                column_order=("DISPLAY_NAME", "Hold", "MINUTES", "KM", "HI_RUN", "TOP_SPEED"),
                use_container_width=True, hide_index=True, height=600
            )
