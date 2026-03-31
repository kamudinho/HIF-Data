import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONFIGURATION (Hvidovre-app værdier) ---
HIF_ROD = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

# --- KONFIGURATION (Dine værdier fra toppen) ---
TEAMS = {
    "Hvidovre": {"ssid": "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"},
    "AaB": {"ssid": "40d5387b-ac2f-4e9b-bb97-34456aeb69c4"},
    "Horsens": {"ssid": "f2b45639-d8e6-4d9b-9371-6f9f1fe2a9d9"},
    "Lyngby": {"ssid": "15af1cc2-5ce6-4552-8a5f-7e233a65cedc"},
    "Esbjerg": {"ssid": "bfc8edb9-96af-4152-a8b0-d096d4271f48"},
    "Kolding": {"ssid": "04aaceac-8a20-422b-8417-9199a519c1b3"},
    "Hobro": {"ssid": "e274c022-4cf1-4c4d-9555-4c6dd38b1224"},
    "HB Køge": {"ssid": "2dccb353-4598-4f35-845d-c6c55c9f5672"},
    "Hillerød": {"ssid": "e274c022-4cf1-4c4d-9555-4c6dd38b1224"},
    "B 93": {"ssid": "e0bb5b5f-2df2-4fc4-854a-e537bd65a280"}
}

def vis_side(conn, name_map=None):
    # --- 0. CSS TIL AT RYKKE ALT OP ---
    st.markdown("""
        <style>
            /* 1. Fjern Streamlits standard top-padding */
            .stAppViewBlockContainer {
                padding-top: 0px !important;
            }
            div.block-container {
                padding-top: 1rem !important;
                max-width: 98% !important;
            }
            
            /* 2. Ryk kolonne-headeren op */
            [data-testid="stHorizontalBlock"] {
                margin-top: -25px !important;
                margin-bottom: -10px !important;
            }

            /* 3. Skjul label i dropdown og gør den kompakt */
            div[data-testid="stSelectbox"] label { display: none; }
            div[data-testid="stSelectbox"] { margin-top: -5px; }

            /* 4. TABS: Fjern luft mellem header og tabs */
            .stTabs { margin-top: 0px; }
            div[data-baseweb="tab-panel"] {
                padding-top: 20px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. DROPDOWN ---
    header_col, select_col = st.columns([3, 1])
    with select_col:
        alle_hold = sorted(list(TEAMS.keys()))
        valgt_hold = st.selectbox(" ", alle_hold, index=alle_hold.index("Hvidovre"))
        v_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. DYNAMISK SQL ---
    @st.cache_data(ttl=600)
    def get_phys_data(ssid):
        sql = f"""
        WITH team_player_ids AS (
            SELECT DISTINCT 
                m.MATCH_SSIID, 
                f.value:"optaId"::string AS player_opta_id
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m,
            LATERAL FLATTEN(input => CASE 
                WHEN m.HOME_SSIID = '{ssid}' THEN m.HOME_PLAYERS 
                ELSE m.AWAY_PLAYERS 
            END) f
            WHERE m.HOME_SSIID = '{ssid}' OR m.AWAY_SSIID = '{ssid}'
        )
        SELECT 
            p.*, 
            h.player_opta_id
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        INNER JOIN team_player_ids h 
            ON p.MATCH_SSIID = h.MATCH_SSIID 
            AND p."optaId" = h.player_opta_id
        WHERE p.MATCH_DATE >= '2025-07-01'
        """
        return conn.query(sql)

    df_phys = get_phys_data(v_ssid)

    if df_phys.empty:
        st.warning(f"Ingen data fundet for {valgt_hold}")
        return

    # --- 3. NAVNE-MAPPING LOGIK (Genbrugelig) ---
    df_local = load_local_players()
    p_map = {}
    if df_local is not None:
        loc_cols = {c.lower(): c for c in df_local.columns}
        oid_col = loc_cols.get('optaid', 'optaId')
        df_local['clean_oid'] = df_local[oid_col].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")
        p_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

    # Funktion til at parse minutter (05:30 -> 5.5)
    def parse_mins(v):
        if pd.isna(v) or v == "": return 0.0
        v_s = str(v)
        if ':' in v_s:
            try:
                m, s = map(int, v_s.split(':'))
                return round(m + s/60, 2)
            except: return 0.0
        return pd.to_numeric(v_s, errors='coerce') or 0.0

    # --- 4. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_hold} Oversigt", "Grafisk", "Top 5 (Liga)", "Kampanalyse"])

    with t1:
        df_phys['MINS_DEC'] = df_phys['MINUTES'].apply(parse_mins)
        df_phys['HI_RUN_CALC'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
        df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: p_map.get(str(r['PLAYER_OPTA_ID']), r['PLAYER_NAME']), axis=1)

        summary = df_phys.groupby('DISPLAY_NAME').agg({
            'MINS_DEC': 'sum', 'DISTANCE': 'sum', 'HI_RUN_CALC': 'sum', 'TOP_SPEED': 'max'
        }).reset_index()
        
        summary = summary[summary['MINS_DEC'] > 10].copy()
        summary['KM/90'] = (summary['DISTANCE'] / summary['MINS_DEC']) * 90 / 1000
        summary['HI m/90'] = (summary['HI_RUN_CALC'] / summary['MINS_DEC']) * 90

        st.dataframe(
            summary.sort_values('KM/90', ascending=False),
            column_config={
                "KM/90": st.column_config.NumberColumn(format="%.2f"),
                "HI m/90": st.column_config.NumberColumn(format="%d"),
                "TOP_SPEED": st.column_config.NumberColumn(format="%.1f")
            },
            use_container_width=True, hide_index=True, height=700
        )

    with t2:
        valg = st.selectbox("Vælg parameter", ["KM/90", "HI m/90", "TOP_SPEED"])
        fig = px.bar(summary.sort_values(valg, ascending=False), x='DISPLAY_NAME', y=valg, color_discrete_sequence=[HIF_ROD])
        st.plotly_chart(fig, use_container_width=True)

    with t3:
        # Snowflake kræver ofte anførselstegn om "HIGH SPEED RUNNING" pga mellemrum
        df_top = conn.query('SELECT PLAYER_NAME, TOP_SPEED, "HIGH SPEED RUNNING" + SPRINTING as HI_TOTAL FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS')
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Topfart (Liga)**")
            st.dataframe(df_top.nlargest(5, 'TOP_SPEED')[['PLAYER_NAME', 'TOP_SPEED']], hide_index=True)
        with c2:
            st.write("**HI Meter (Liga total)**")
            st.dataframe(df_top.nlargest(5, 'HI_TOTAL')[['PLAYER_NAME', 'HI_TOTAL']], hide_index=True)

    with t4:
        df_meta = conn.query(f"""
            SELECT TO_VARCHAR("DATE", 'YYYY-MM-DD') as DATE_STR, DESCRIPTION, MATCH_SSIID 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA 
            WHERE (HOME_SSIID = '{v_ssid}' OR AWAY_SSIID = '{v_ssid}')
            AND "DATE" >= '2025-07-01'
            ORDER BY "DATE" DESC
        """)
        
        if not df_meta.empty:
            df_meta['LABEL'] = df_meta['DATE_STR'] + " - " + df_meta['DESCRIPTION']
            v_kamp = st.selectbox("Vælg kamp", df_meta['LABEL'].unique())
            m_id = df_meta[df_meta['LABEL'] == v_kamp].iloc[0]['MATCH_SSIID']
            
            # Hent valide IDs for det valgte hold i denne kamp
            ids_df = conn.query(f"""
                SELECT f.value:"optaId"::string AS tid
                FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m,
                LATERAL FLATTEN(input => CASE 
                    WHEN m.HOME_SSIID = '{v_ssid}' THEN m.HOME_PLAYERS 
                    ELSE m.AWAY_PLAYERS 
                END) f
                WHERE m.MATCH_SSIID = '{m_id}'
            """)
            list_valid_ids = ids_df['TID'].tolist()
            
            # Hent kampdata
            df_m = conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_SSIID = '{m_id}'")
            
            if not df_m.empty:
                # Behandling af kamp-specifik data
                df_m['KM'] = (df_m['DISTANCE'] / 1000).round(2)
                df_m['HI_RUN'] = df_m['HIGH SPEED RUNNING'].fillna(0) + df_m['SPRINTING'].fillna(0)
                # Vigtigt: Navne-mapping her også!
                df_m['DISPLAY_NAME'] = df_m.apply(lambda r: p_map.get(str(r['optaId']), r['PLAYER_NAME']), axis=1)
                df_m['Hold'] = df_m['optaId'].apply(lambda x: valgt_hold if str(x) in list_valid_ids else "Modstander")

                st.dataframe(
                    df_m.sort_values(by=['Hold', 'DISTANCE'], ascending=[True, False]),
                    column_config={
                        "DISPLAY_NAME": "Spiller",
                        "MINUTES": "Min",
                        "KM": st.column_config.NumberColumn("KM", format="%.2f"),
                        "HI_RUN": "HI m",
                        "TOP_SPEED": "Top"
                    },
                    column_order=("DISPLAY_NAME", "Hold", "MINUTES", "KM", "HI_RUN", "TOP_SPEED"),
                    use_container_width=True, hide_index=True, height=700
                )
