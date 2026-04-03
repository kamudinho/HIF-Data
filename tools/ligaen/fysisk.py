import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 
from data.utils.team_mapping import TEAMS, TEAM_COLORS

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
    # Vi tager kun de hold der har et 'ssid' defineret
    hold_med_data = sorted([k for k, v in TEAMS.items() if "ssid" in v])
    
    header_col, select_col = st.columns([3, 1])
    with select_col:
        valgt_hold = st.selectbox(" ", hold_med_data, index=hold_med_data.index("Hvidovre"))
        v_ssid = TEAMS[valgt_hold]["ssid"]

    # --- 2. OMREGNINGSFUNKTIONER (Meter til KM og Sek til Min) ---
    def parse_to_mins(v):
        """Omregner 'MM:SS' eller rå sekunder til decimal-minutter"""
        if pd.isna(v) or v == "": return 0.0
        s = str(v)
        if ':' in s:
            parts = s.split(':')
            return float(parts[0]) + (float(parts[1])/60)
        try:
            val = float(s)
            # Hvis tallet er meget højt (f.eks. 5400), antager vi det er sekunder og dividerer med 60
            return val / 60 if val > 500 else val 
        except: return 0.0

    # --- 3. DYNAMISK SQL ---
    @st.cache_data(ttl=600)
    def get_phys_data(ssid):
        # Vi henter HOME_SSIID og AWAY_SSIID med ud så vi kan mappe holdnavne bagefter
        sql = f"""
        WITH team_player_ids AS (
            SELECT DISTINCT 
                m.MATCH_SSIID, 
                m.HOME_SSIID,
                m.AWAY_SSIID,
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
            h.player_opta_id,
            h.HOME_SSIID,
            h.AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        INNER JOIN team_player_ids h 
            ON p.MATCH_SSIID = h.MATCH_SSIID 
            AND p."optaId" = h.player_opta_id
        WHERE p.MATCH_DATE >= '2025-07-01'
        """
        return conn.query(sql)

    df_phys = get_phys_data(v_ssid)
    # Tving alle kolonnenavne til UPPER for stabilitet
    df_phys.columns = [c.upper() for c in df_phys.columns]

    # --- 4. NAVNE-MAPPING LOGIK ---
    df_local = load_local_players()
    p_map = {}
    if df_local is not None:
        oid_col = next((c for c in df_local.columns if c.lower() == 'optaid'), 'optaId')
        df_local['clean_oid'] = df_local[oid_col].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")
        p_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

    # SSID til Navn oversætter (fra din TEAM_MAPPING)
    ssid_to_name = {v['ssid']: k for k, v in TEAMS.items() if 'ssid' in v}

    # --- 5. TABS ---
    t1, t2, t3, t4 = st.tabs([f"{valgt_hold} Oversigt", "Grafisk", "Top 5 (Liga)", "Kampanalyse"])

    with t1:
        if df_phys.empty:
            st.warning(f"Ingen data fundet for {valgt_hold}")
        else:
            # Omregninger
            df_phys['MINS_DEC'] = df_phys['MINUTES'].apply(parse_to_mins)
            df_phys['HI_RUN_CALC'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
            df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: p_map.get(str(r['PLAYER_OPTA_ID']), r['PLAYER_NAME']), axis=1)

            summary = df_phys.groupby('DISPLAY_NAME').agg({
                'MINS_DEC': 'sum', 
                'DISTANCE': 'sum', 
                'HI_RUN_CALC': 'sum', 
                'TOP_SPEED': 'max'
            }).reset_index()

            # Filter spillere med meget lidt tid (under 5 min totalt)
            summary = summary[summary['MINS_DEC'] > 5].copy()
            
            # Beregning pr. 90 (DISTANCE / 1000 for at få KM)
            summary['KM/90'] = (summary['DISTANCE'] / 1000 / summary['MINS_DEC']) * 90
            summary['HI m/90'] = (summary['HI_RUN_CALC'] / summary['MINS_DEC']) * 90

            st.dataframe(
                summary.sort_values('KM/90', ascending=False),
                column_config={
                    "DISPLAY_NAME": "Spiller",
                    "MINS_DEC": st.column_config.NumberColumn("Total Min", format="%d min"),
                    "KM/90": st.column_config.NumberColumn("KM/90", format="%.2f km"),
                    "HI m/90": st.column_config.NumberColumn("HI m/90", format="%d m"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
                },
                use_container_width=True, hide_index=True, height=700
            )

    with t3:
        # Liga Top 5 - Her bruger vi SQL til at summere alt
        df_league = conn.query("""
            SELECT 
                PLAYER_NAME, 
                "optaId" as OPTAID,
                SUM(DISTANCE) as TOTAL_DIST,
                SUM("HIGH SPEED RUNNING" + SPRINTING) as TOTAL_HI,
                MAX(TOP_SPEED) as MAX_SPEED,
                SUM(CASE 
                    WHEN MINUTES LIKE '%:%' THEN CAST(SPLIT_PART(MINUTES, ':', 1) AS FLOAT) + CAST(SPLIT_PART(MINUTES, ':', 2) AS FLOAT)/60
                    ELSE CAST(MINUTES AS FLOAT) / 60 
                END) as TOTAL_MINS
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            GROUP BY PLAYER_NAME, "optaId"
            HAVING TOTAL_MINS > 90
        """)

        df_league['KM/90'] = (df_league['TOTAL_DIST'] / 1000 / df_league['TOTAL_MINS']) * 90
        df_league['HI/90'] = (df_league['TOTAL_HI'] / df_league['TOTAL_MINS']) * 90

        c1, c2, c3 = st.columns(3)
        col_sets = [
            (c1, "MAX_SPEED", "Topfart (Max)", "%.1f km/t"),
            (c2, "KM/90", "KM pr. 90", "%.2f km"),
            (c3, "HI/90", "HI m pr. 90", "%d m")
        ]

        for col, key, title, fmt in col_sets:
            with col:
                st.write(f"**{title}**")
                st.dataframe(
                    df_league.nlargest(5, key)[['PLAYER_NAME', key]],
                    column_config={key: st.column_config.NumberColumn("Værdi", format=fmt)},
                    hide_index=True, use_container_width=True
                )

    with t4:
        # Kampanalyse (Mapping af HOME/AWAY SSIID til Holdnavne)
        df_meta = conn.query(f"""
            SELECT DISTINCT 
                TO_VARCHAR(m."DATE", 'YYYY-MM-DD') as DATE_STR, 
                m.DESCRIPTION, 
                m.MATCH_SSIID,
                m.HOME_SSIID,
                m.AWAY_SSIID
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA m
            JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p ON m.MATCH_SSIID = p.MATCH_SSIID
            WHERE m.HOME_SSIID = '{v_ssid}' OR m.AWAY_SSIID = '{v_ssid}'
            ORDER BY DATE_STR DESC
        """)
        
        if not df_meta.empty:
            df_meta['LABEL'] = df_meta['DATE_STR'] + " - " + df_meta['DESCRIPTION']
            v_kamp = st.selectbox("Vælg kamp", df_meta['LABEL'].unique())
            row = df_meta[df_meta['LABEL'] == v_kamp].iloc[0]
            
            df_m = conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_SSIID = '{row['MATCH_SSIID']}'")
            df_m.columns = [c.upper() for c in df_m.columns]
            
            if not df_m.empty:
                df_m['KM'] = df_m['DISTANCE'] / 1000
                df_m['HI_RUN'] = df_m['HIGH SPEED RUNNING'].fillna(0) + df_m['SPRINTING'].fillna(0)
                
                # Her Mapper vi holdnavnet via SSIID fra din TEAM_MAPPING
                df_m['HOLD'] = df_m.apply(lambda r: ssid_to_name.get(row['HOME_SSIID'], "Hjemme") if r['TEAMID'] == row['HOME_SSIID'] else ssid_to_name.get(row['AWAY_SSIID'], "Ude"), axis=1)
                
                st.dataframe(
                    df_m[['PLAYER_NAME', 'HOLD', 'MINUTES', 'KM', 'HI_RUN', 'TOP_SPEED']].sort_values('KM', ascending=False),
                    column_config={
                        "PLAYER_NAME": "Spiller",
                        "KM": st.column_config.NumberColumn("KM", format="%.2f km"),
                        "HI_RUN": st.column_config.NumberColumn("HI m", format="%d m")
                    },
                    use_container_width=True, hide_index=True
                )
