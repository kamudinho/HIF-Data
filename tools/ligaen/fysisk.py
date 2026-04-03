import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
HIF_ROD = '#cc0000'

def vis_side(conn, name_map=None):
    # --- 0. CSS TIL OPSÆTNING ---
    st.markdown("""
        <style>
            .stAppViewBlockContainer { padding-top: 0px !important; }
            div.block-container { padding-top: 1rem !important; max-width: 98% !important; }
            div[data-testid="stSelectbox"] label { display: none; }
            .stTabs { margin-top: 0px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. DROPDOWN (Baseret på din TEAMS mapping) ---
    hold_med_data = sorted([k for k, v in TEAMS.items() if "ssid" in v])
    
    header_col, select_col = st.columns([3, 1])
    with select_col:
        valgt_hold = st.selectbox(" ", hold_med_data, index=hold_med_data.index("Hvidovre"))
        v_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. HJÆLPEFUNKTIONER ---
    def parse_to_mins(v):
        """Omregner 'MM:SS' eller rå sekunder til decimal-minutter"""
        if pd.isna(v) or v == "": return 0.0
        s = str(v)
        if ':' in s:
            parts = s.split(':')
            return float(parts[0]) + (float(parts[1])/60)
        try:
            val = float(s)
            return val / 60 if val > 500 else val 
        except: return 0.0

    def format_dist(meter):
        """Smart formatering: <1000m -> 'm', >1000m -> 'km'"""
        if pd.isna(meter) or meter == 0: return "0 m"
        if meter < 1000:
            return f"{int(meter)} m"
        else:
            return f"{meter/1000:.2f} km"

    # --- 3. DYNAMISK SQL ---
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
    df_phys.columns = [c.upper() for c in df_phys.columns]

    # --- 4. NAVNE-MAPPING ---
    df_local = load_local_players()
    p_map = {}
    if df_local is not None:
        oid_col = next((c for c in df_local.columns if c.lower() == 'optaid'), 'optaId')
        df_local['clean_oid'] = df_local[oid_col].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")
        p_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

    # --- 5. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_hold} Oversigt", "Grafisk", "Top 5 (Liga)", "Kampanalyse"])

    with t1:
        if not df_phys.empty:
            df_phys['MINS_DEC'] = df_phys['MINUTES'].apply(parse_to_mins)
            df_phys['HI_RUN_CALC'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
            df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: p_map.get(str(r['PLAYER_OPTA_ID']), r['PLAYER_NAME']), axis=1)

            summary = df_phys.groupby('DISPLAY_NAME').agg({
                'MINS_DEC': 'sum', 'DISTANCE': 'sum', 'HI_RUN_CALC': 'sum', 'TOP_SPEED': 'max'
            }).reset_index()

            summary = summary[summary['MINS_DEC'] > 5].copy()
            
            # Beregn pr 90 enheder
            summary['KM/90_VAL'] = (summary['DISTANCE'] / 1000 / summary['MINS_DEC']) * 90
            summary['HI/90_VAL'] = (summary['HI_RUN_CALC'] / summary['MINS_DEC']) * 90
            
            # Formater til visning
            summary['KM/90'] = summary['KM/90_VAL'].apply(lambda x: f"{x:.2f} km")
            summary['HI m/90'] = summary['HI/90_VAL'].apply(lambda x: f"{int(x)} m")

            st.dataframe(
                summary[['DISPLAY_NAME', 'MINS_DEC', 'KM/90', 'HI m/90', 'TOP_SPEED']].sort_values('KM/90_VAL', ascending=False),
                column_config={
                    "DISPLAY_NAME": "Spiller",
                    "MINS_DEC": st.column_config.NumberColumn("Total Min", format="%d"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
                },
                use_container_width=True, hide_index=True, height=700
            )

    with t3:
        df_league = conn.query("""
            SELECT 
                PLAYER_NAME, 
                SUM(DISTANCE) as TOTAL_DIST,
                SUM("HIGH SPEED RUNNING" + SPRINTING) as TOTAL_HI,
                MAX(TOP_SPEED) as MAX_SPEED,
                SUM(CASE 
                    WHEN MINUTES LIKE '%:%' THEN CAST(SPLIT_PART(MINUTES, ':', 1) AS FLOAT) + CAST(SPLIT_PART(MINUTES, ':', 2) AS FLOAT)/60
                    ELSE CAST(MINUTES AS FLOAT) / 60 
                END) as TOTAL_MINS
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            GROUP BY PLAYER_NAME
            HAVING TOTAL_MINS > 90
        """)

        df_league['KM/90'] = (df_league['TOTAL_DIST'] / 1000 / df_league['TOTAL_MINS']) * 90
        df_league['HI/90'] = (df_league['TOTAL_HI'] / df_league['TOTAL_MINS']) * 90

        c1, c2, c3 = st.columns(3)
        metrics = [ (c1, "MAX_SPEED", "Topfart", "%.1f km/t"), (c2, "KM/90", "KM pr. 90", "%.2f km"), (c3, "HI/90", "HI m pr. 90", "%d m") ]

        for col, key, title, fmt in metrics:
            with col:
                st.write(f"**{title}**")
                st.dataframe(df_league.nlargest(5, key)[['PLAYER_NAME', key]], hide_index=True, use_container_width=True)

    with t4:
        df_meta = conn.query(f"""
            SELECT DISTINCT TO_VARCHAR(m."DATE", 'YYYY-MM-DD') as DATE_STR, m.DESCRIPTION, m.MATCH_SSIID 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA m
            JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p ON m.MATCH_SSIID = p.MATCH_SSIID
            WHERE m.HOME_SSIID = '{v_ssid}' OR m.AWAY_SSIID = '{v_ssid}'
            ORDER BY DATE_STR DESC
        """)
        
        if not df_meta.empty:
            df_meta['LABEL'] = df_meta['DATE_STR'] + " - " + df_meta['DESCRIPTION']
            v_kamp = st.selectbox("Vælg kamp", df_meta['LABEL'].unique())
            m_id = df_meta[df_meta['LABEL'] == v_kamp].iloc[0]['MATCH_SSIID']
            
            df_m = conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_SSIID = '{m_id}'")
            df_m.columns = [c.upper() for c in df_m.columns]
            
            if not df_m.empty:
                # Smart distance formatering her
                df_m['SMART_DIST'] = df_m['DISTANCE'].apply(format_dist)
                df_m['HI_RUN'] = (df_m['HIGH SPEED RUNNING'].fillna(0) + df_m['SPRINTING'].fillna(0)).apply(lambda x: f"{int(x)} m")
                
                oid_col = 'OPTAID' if 'OPTAID' in df_m.columns else 'optaId'
                df_m['SPIL'] = df_m.apply(lambda r: p_map.get(str(r.get(oid_col)), r['PLAYER_NAME']), axis=1)
                
                st.dataframe(
                    df_m[['SPIL', 'MINUTES', 'SMART_DIST', 'HI_RUN', 'TOP_SPEED']].sort_values('SMART_DIST', ascending=False),
                    column_config={
                        "SPIL": "Spiller",
                        "MINUTES": "Min",
                        "SMART_DIST": "Distance",
                        "HI_RUN": "HI løb",
                        "TOP_SPEED": st.column_config.NumberColumn("Top", format="%.1f km/t")
                    },
                    use_container_width=True, hide_index=True
                )
