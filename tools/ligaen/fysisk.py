import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONFIGURATION ---
HIF_ROD = '#cc0000'

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
    st.markdown("""
        <style>
            .stAppViewBlockContainer { padding-top: 0px !important; }
            div.block-container { padding-top: 1rem !important; max-width: 98% !important; }
            [data-testid="stHorizontalBlock"] { margin-top: -25px !important; margin-bottom: -10px !important; }
            div[data-testid="stSelectbox"] label { display: none; }
            .stTabs { margin-top: 0px; }
            div[data-baseweb="tab-panel"] { padding-top: 20px !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. DROPDOWN ---
    header_col, select_col = st.columns([3, 1])
    with select_col:
        alle_hold = sorted(list(TEAMS.keys()))
        valgt_hold = st.selectbox(" ", alle_hold, index=alle_hold.index("Hvidovre"))
        v_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. DYNAMISK SQL (Oversigt) ---
    @st.cache_data(ttl=600)
    def get_phys_data(ssid):
        # Bruger anførselstegn om "optaId" for at undgå Snowflake fejl
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

    # --- 3. NAVNE-MAPPING ---
    df_local = load_local_players()
    p_map = {}
    if df_local is not None:
        oid_col = next((c for c in df_local.columns if c.lower() == 'optaid'), 'optaId')
        df_local['clean_oid'] = df_local[oid_col].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")
        p_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

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
        if df_phys.empty:
            st.warning("Ingen data fundet.")
        else:
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
                    "KM/90": st.column_config.NumberColumn("KM/90", format="%.2f km"),
                    "HI m/90": st.column_config.NumberColumn("HI m/90", format="%d m"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
                },
                use_container_width=True, hide_index=True, height=700
            )

    with t2:
        if not df_phys.empty:
            valg = st.selectbox("Vælg parameter", ["KM/90", "HI m/90", "TOP_SPEED"])
            fig = px.bar(
                summary.sort_values(valg, ascending=False), 
                x='DISPLAY_NAME', y=valg, 
                color_discrete_sequence=[HIF_ROD],
                text_auto='.2f' if valg != "HI m/90" else 'd'
            )
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    with t3:
        # RETTET SQL: Bruger dobbelte anførselstegn konsekvent for kolonnenavne med mellemrum eller små bogstaver
        df_league = conn.query("""
            SELECT 
                PLAYER_NAME, 
                "teamName" as KLUB,
                MAX(TOP_SPEED) as MAX_SPEED,
                SUM(DISTANCE) as TOTAL_DIST,
                SUM("HIGH SPEED RUNNING" + "SPRINTING") as TOTAL_HI,
                SUM(CAST(SPLIT_PART(MINUTES, ':', 1) AS FLOAT) + CAST(SPLIT_PART(MINUTES, ':', 2) AS FLOAT)/60) as TOTAL_MINS
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            GROUP BY PLAYER_NAME, "teamName"
            HAVING TOTAL_MINS > 90
        """)

        df_league['KM/90'] = (df_league['TOTAL_DIST'] / df_league['TOTAL_MINS']) * 90 / 1000
        df_league['HI/90'] = (df_league['TOTAL_HI'] / df_league['TOTAL_MINS']) * 90

        c1, c2, c3 = st.columns(3)
        col_set = {
            "MAX_SPEED": ["Topfart", "%.1f km/t", c1, "Topfart (Max)"],
            "KM/90": ["Distance", "%.2f km", c2, "KM pr. 90"],
            "HI/90": ["HI løb", "%d m", c3, "HI m pr. 90"]
        }

        for key, (label, fmt, col, title) in col_set.items():
            with col:
                st.write(f"**{title}**")
                st.dataframe(
                    df_league.nlargest(5, key)[['PLAYER_NAME', 'KLUB', key]],
                    column_config={
                        "PLAYER_NAME": "Navn",
                        "KLUB": "Klub",
                        key: st.column_config.NumberColumn(label, format=fmt)
                    },
                    hide_index=True, use_container_width=True
                )

    with t4:
        df_meta = conn.query(f"""
            SELECT DISTINCT
                TO_VARCHAR(m."DATE", 'YYYY-MM-DD') as DATE_STR, 
                m.DESCRIPTION, 
                m.MATCH_SSIID 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA m
            INNER JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p 
                ON m.MATCH_SSIID = p.MATCH_SSIID
            WHERE (m.HOME_SSIID = '{v_ssid}' OR m.AWAY_SSIID = '{v_ssid}')
            AND m."DATE" >= '2025-07-01'
            ORDER BY DATE_STR DESC
        """)
        
        if df_meta.empty:
            st.info("Ingen kampdata fundet.")
        else:
            df_meta['LABEL'] = df_meta['DATE_STR'] + " - " + df_meta['DESCRIPTION']
            v_kamp = st.selectbox("Vælg kamp", df_meta['LABEL'].unique())
            m_id = df_meta[df_meta['LABEL'] == v_kamp].iloc[0]['MATCH_SSIID']
            
            df_m = conn.query(f'SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_SSIID = "{m_id}"')
            
            if not df_m.empty:
                df_m['KM'] = (df_m['DISTANCE'] / 1000)
                df_m['HI_RUN'] = df_m['HIGH SPEED RUNNING'].fillna(0) + df_m['SPRINTING'].fillna(0)
                
                oid_col = 'optaId' if 'optaId' in df_m.columns else 'OPTAID'
                df_m['DISPLAY_NAME'] = df_m.apply(lambda r: p_map.get(str(r[oid_col]), r['PLAYER_NAME']), axis=1)
                
                st.dataframe(
                    df_m.sort_values(by=['teamName', 'DISTANCE'], ascending=[True, False]),
                    column_config={
                        "DISPLAY_NAME": "Spiller",
                        "teamName": "Hold",
                        "MINUTES": "Min",
                        "KM": st.column_config.NumberColumn("KM", format="%.2f km"),
                        "HI_RUN": st.column_config.NumberColumn("HI m", format="%d m"),
                        "TOP_SPEED": st.column_config.NumberColumn("Top", format="%.1f km/t")
                    },
                    column_order=("DISPLAY_NAME", "teamName", "MINUTES", "KM", "HI_RUN", "TOP_SPEED"),
                    use_container_width=True, hide_index=True, height=600
                )
