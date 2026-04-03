import streamlit as st
import pandas as pd
import plotly.express as px
from data.data_load import load_local_players 
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
HIF_ROD = '#cc0000'

def vis_side(conn, name_map=None):
    st.markdown("""
        <style>
            .stAppViewBlockContainer { padding-top: 0px !important; }
            div.block-container { padding-top: 1rem !important; max-width: 98% !important; }
            div[data-testid="stSelectbox"] label { display: none; }
            .stTabs { margin-top: 0px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. DROPDOWN ---
    hold_med_data = sorted([k for k, v in TEAMS.items() if "ssid" in v])
    header_col, select_col = st.columns([3, 1])
    with select_col:
        valgt_hold = st.selectbox(" ", hold_med_data, index=hold_med_data.index("Hvidovre"))
        v_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. HJÆLPEFUNKTIONER ---
    def parse_to_mins(v):
        if pd.isna(v) or v == "": return 0.0
        s = str(v)
        if ':' in s:
            try:
                parts = s.split(':')
                return float(parts[0]) + (float(parts[1])/60)
            except: return 0.0
        try:
            val = float(s)
            return val / 60 if val > 500 else val 
        except: return 0.0

    def format_smart_dist(meter):
        """Konverterer til km hvis over 1000, ellers bliver det i meter"""
        try:
            m = float(meter)
            if m < 1000:
                return f"{int(m)} m"
            else:
                return f"{m/1000:.2f} km"
        except:
            return "0 m"

    # --- 3. DATA LOAD ---
    @st.cache_data(ttl=600)
    def get_phys_data(ssid):
        sql = f"""
        WITH team_player_ids AS (
            SELECT DISTINCT m.MATCH_SSIID, f.value:"optaId"::string AS player_opta_id
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m,
            LATERAL FLATTEN(input => CASE WHEN m.HOME_SSIID = '{ssid}' THEN m.HOME_PLAYERS ELSE m.AWAY_PLAYERS END) f
            WHERE m.HOME_SSIID = '{ssid}' OR m.AWAY_SSIID = '{ssid}'
        )
        SELECT p.*, h.player_opta_id
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        INNER JOIN team_player_ids h ON p.MATCH_SSIID = h.MATCH_SSIID AND p."optaId" = h.player_opta_id
        WHERE p.MATCH_DATE >= '2025-07-01'
        """
        return conn.query(sql)

    df_phys = get_phys_data(v_ssid)
    df_phys.columns = [c.upper() for c in df_phys.columns]

    # Navne-mapping
    df_local = load_local_players()
    p_map = {}
    if df_local is not None:
        oid_col = next((c for c in df_local.columns if c.lower() == 'optaid'), 'optaId')
        df_local['clean_oid'] = df_local[oid_col].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")
        p_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

    # --- 4. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_hold} Oversigt", "Grafisk", "Top 5 (Liga)", "Kampanalyse"])

    with t1:
        if df_phys.empty:
            st.warning("Ingen data fundet.")
        else:
            # Beregninger
            df_phys['MINS_DEC'] = df_phys['MINUTES'].apply(parse_to_mins)
            df_phys['HI_RUN_TOTAL'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
            df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: p_map.get(str(r['PLAYER_OPTA_ID']), r['PLAYER_NAME']), axis=1)

            summary = df_phys.groupby('DISPLAY_NAME').agg({
                'MINS_DEC': 'sum', 'DISTANCE': 'sum', 'HI_RUN_TOTAL': 'sum', 'TOP_SPEED': 'max'
            }).reset_index()

            summary = summary[summary['MINS_DEC'] > 5].copy()
            
            # Lav numeriske værdier til sortering
            summary['KM90_NUM'] = (summary['DISTANCE'] / 1000 / summary['MINS_DEC']) * 90
            summary['HI90_NUM'] = (summary['HI_RUN_TOTAL'] / summary['MINS_DEC']) * 90
            
            # Lav smart-tekst til visning
            summary['KM/90'] = summary['KM90_NUM'].apply(lambda x: f"{x:.2f} km" if x >= 1 else f"{int(x*1000)} m")
            summary['HI m/90'] = summary['HI90_NUM'].apply(lambda x: f"{int(x)} m")

            st.dataframe(
                summary[['DISPLAY_NAME', 'MINS_DEC', 'KM/90', 'HI m/90', 'TOP_SPEED', 'KM90_NUM']].sort_values('KM90_NUM', ascending=False),
                column_config={
                    "DISPLAY_NAME": "Spiller",
                    "MINS_DEC": st.column_config.NumberColumn("Minutter", format="%d"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t"),
                    "KM90_NUM": None # Skjul sorterings-kolonnen
                },
                use_container_width=True, hide_index=True, height=600
            )

    with t3:
        df_league = conn.query("""
            SELECT PLAYER_NAME, SUM(DISTANCE) as TOTAL_DIST, SUM("HIGH SPEED RUNNING" + SPRINTING) as TOTAL_HI, MAX(TOP_SPEED) as MAX_SPEED,
            SUM(CASE WHEN MINUTES LIKE '%:%' THEN CAST(SPLIT_PART(MINUTES, ':', 1) AS FLOAT) + CAST(SPLIT_PART(MINUTES, ':', 2) AS FLOAT)/60 ELSE CAST(MINUTES AS FLOAT) / 60 END) as TOTAL_MINS
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS GROUP BY PLAYER_NAME HAVING TOTAL_MINS > 90
        """)
        
        df_league['KM/90_VAL'] = (df_league['TOTAL_DIST'] / 1000 / df_league['TOTAL_MINS']) * 90
        df_league['HI/90_VAL'] = (df_league['TOTAL_HI'] / df_league['TOTAL_MINS']) * 90
        
        # Formater liga-data med smart distance
        df_league['Distance'] = df_league['KM/90_VAL'].apply(lambda x: f"{x:.2f} km")
        df_league['HI Løb'] = df_league['HI/90_VAL'].apply(lambda x: f"{int(x)} m")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("**Topfart**")
            st.dataframe(df_league.nlargest(5, 'MAX_SPEED')[['PLAYER_NAME', 'MAX_SPEED']], hide_index=True)
        with c2:
            st.write("**KM pr. 90**")
            st.dataframe(df_league.nlargest(5, 'KM/90_VAL')[['PLAYER_NAME', 'Distance']], hide_index=True)
        with c3:
            st.write("**HI m pr. 90**")
            st.dataframe(df_league.nlargest(5, 'HI/90_VAL')[['PLAYER_NAME', 'HI Løb']], hide_index=True)

    with t4:
        df_meta = conn.query(f"SELECT DISTINCT TO_VARCHAR(m.\"DATE\", 'YYYY-MM-DD') as DATE_STR, m.DESCRIPTION, m.MATCH_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA m JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p ON m.MATCH_SSIID = p.MATCH_SSIID WHERE m.HOME_SSIID = '{v_ssid}' OR m.AWAY_SSIID = '{v_ssid}' ORDER BY DATE_STR DESC")
        
        if not df_meta.empty:
            df_meta['LABEL'] = df_meta['DATE_STR'] + " - " + df_meta['DESCRIPTION']
            v_kamp = st.selectbox("Vælg kamp", df_meta['LABEL'].unique())
            m_id = df_meta[df_meta['LABEL'] == v_kamp].iloc[0]['MATCH_SSIID']
            
            df_m = conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_SSIID = '{m_id}'")
            df_m.columns = [c.upper() for c in df_m.columns]
            
            if not df_m.empty:
                # SMART DISTANCE IMPLEMENTERING
                df_m['SMART_DIST'] = df_m['DISTANCE'].apply(format_smart_dist)
                df_m['HI_VAL'] = df_m['HIGH SPEED RUNNING'].fillna(0) + df_m['SPRINTING'].fillna(0)
                df_m['HI_DISPLAY'] = df_m['HI_VAL'].apply(lambda x: f"{int(x)} m")
                
                oid_col = 'OPTAID' if 'OPTAID' in df_m.columns else 'optaId'
                df_m['SPIL'] = df_m.apply(lambda r: p_map.get(str(r.get(oid_col)), r['PLAYER_NAME']), axis=1)
                
                st.dataframe(
                    df_m[['SPIL', 'MINUTES', 'SMART_DIST', 'HI_DISPLAY', 'TOP_SPEED']].sort_values('SMART_DIST', ascending=False),
                    column_config={
                        "SPIL": "Spiller", "MINUTES": "Min", "SMART_DIST": "Distance", "HI_DISPLAY": "HI løb",
                        "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
                    },
                    use_container_width=True, hide_index=True
                )
