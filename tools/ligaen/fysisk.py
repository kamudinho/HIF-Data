import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

# Spillere der skal udelukkes (optaId)
EXCLUDE_LIST = ["114516", "570705", "624707", "523647", "39664"] 

def vis_side(conn, name_map=None):
    # --- 1. HENT LOKAL MAPPING (players.csv) ---
    df_local = load_local_players()
    player_mapping = {}
    
    if df_local is not None and not df_local.empty:
        df_local.columns = [c.strip() for c in df_local.columns]
        if 'optaId' in df_local.columns and 'NAVN' in df_local.columns:
            df_local['optaId'] = df_local['optaId'].astype(str).str.split('.').str[0].str.strip()
            player_mapping = df_local.set_index('optaId')['NAVN'].to_dict()

    # --- 2. HENT DATA FRA SNOWFLAKE ---
    @st.cache_data(ttl=600)
    def get_safe_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Metadata for kampe
        query_meta = f"""
        SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND "DATE" >= '2025-07-01'
          AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
        """
        df_meta = conn.query(query_meta)
        
        if df_meta.empty:
            return pd.DataFrame(), pd.DataFrame()

        # SQL logik til at identificere Hvidovre spillere
        query_phys = f"""
        WITH hvidovre_ids AS (
            SELECT DISTINCT 
                m.MATCH_SSIID,
                f.value:"optaId"::string AS opta_id
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m,
            LATERAL FLATTEN(input => 
                CASE 
                    WHEN m.HOME_SSIID = '{HIF_SSIID}' THEN m.HOME_PLAYERS 
                    ELSE m.AWAY_PLAYERS 
                END
            ) f
            WHERE m.HOME_SSIID = '{HIF_SSIID}' OR m.AWAY_SSIID = '{HIF_SSIID}'
        )
        SELECT 
            p.MATCH_SSIID, p.PLAYER_NAME, p."optaId", p.MINUTES, 
            p.DISTANCE, p."HIGH SPEED RUNNING", p."SPRINTING", p."TOP_SPEED",
            p."NO_OF_HIGH_INTENSITY_RUNS",
            CASE WHEN h.opta_id IS NOT NULL THEN 'Hvidovre IF' ELSE 'Modstander' END AS "Hold"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        LEFT JOIN hvidovre_ids h ON p.MATCH_SSIID = h.MATCH_SSIID AND p."optaId" = h.opta_id
        WHERE p.MATCH_SSIID IN (SELECT MATCH_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA WHERE "DATE" >= '2025-07-01')
        """
        df_phys = conn.query(query_phys)
        return df_meta, df_phys

    df_meta, df_phys = get_safe_data()

    if df_phys.empty:
        st.error("Ingen data fundet.")
        return

    # --- 3. DATABEHANDLING ---
    def parse_minutes(val):
        try:
            val_str = str(val)
            if ':' in val_str:
                m, s = map(int, val_str.split(':'))
                return round(m + s/60, 2)
            return float(val)
        except: return 0.0

    df_phys['MINS_DECIMAL'] = df_phys['MINUTES'].apply(parse_minutes)
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'] + df_phys['SPRINTING']

    # Ekskluder spillere
    df_phys = df_phys[~df_phys['optaId'].astype(str).str.split('.').str[0].isin(EXCLUDE_LIST)].copy()

    # Map navne fra CSV
    def map_display_name(row):
        oid = str(row['optaId']).strip()
        return player_mapping.get(oid, row['PLAYER_NAME'])

    df_phys['DISPLAY_NAME'] = df_phys.apply(map_display_name, axis=1)

    # --- 4. VISNING ---
    t1, t2, t3, t4 = st.tabs(["Hvidovre IF (P90)", "Graf", "Top 5-oversigt", "Kampoversigt"])

    with t1:
        df_hif = df_phys[df_phys['Hold'] == "Hvidovre IF"].copy()
        summary = df_hif.groupby('DISPLAY_NAME').agg({
            'MINS_DECIMAL': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'SPRINTING': 'sum',
            'TOP_SPEED': 'max',
            'NO_OF_HIGH_INTENSITY_RUNS': 'sum'
        }).reset_index()

        summary = summary[summary['MINS_DECIMAL'] > 15].copy()
        summary['Dist_P90'] = (summary['DISTANCE'] / summary['MINS_DECIMAL']) * 90 / 1000
        summary['HI_P90'] = (summary['HI_RUN'] / summary['MINS_DECIMAL']) * 90
        summary['Sprint_P90'] = (summary['SPRINTING'] / summary['MINS_DECIMAL']) * 90
        summary['HIR_Actions_P90'] = (summary['NO_OF_HIGH_INTENSITY_RUNS'] / summary['MINS_DECIMAL']) * 90

        st.dataframe(
            summary.sort_values('Dist_P90', ascending=False), 
            column_config={
                "DISPLAY_NAME": "Spiller",
                "Dist_P90": st.column_config.NumberColumn("KM pr. 90", format="%.2f km"),
                "HI_P90": st.column_config.NumberColumn("HI m pr. 90", format="%d m"),
                "Sprint_P90": st.column_config.NumberColumn("Sprint pr. 90", format="%d m"),
                "HIR_Actions_P90": st.column_config.NumberColumn("HI Aktioner P90", format="%.1f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            use_container_width=True, hide_index=True
        )

    with t3:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Topfart (km/t)**")
            st.table(df_phys.groupby('DISPLAY_NAME')['TOP_SPEED'].max().nlargest(5).map(lambda x: f"{x:.1f} km/t"))
        with c2:
            st.write("**HI løb i én kamp (m)**")
            st.table(df_phys.nlargest(5, 'HI_RUN')[['DISPLAY_NAME', 'HI_RUN']].set_index('DISPLAY_NAME'))

    with t4:
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique())
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
            df_match['KM'] = df_match['DISTANCE'] / 1000
            
            # --- SORTERING: Kun Distance ---
            df_match = df_match.sort_values(by='DISTANCE', ascending=False)
            
            st.dataframe(
                df_match[['DISPLAY_NAME', 'Hold', 'MINUTES', 'KM', 'HI_RUN', 'SPRINTING', 'TOP_SPEED']], 
                use_container_width=True, hide_index=True,
                column_config={
                    "KM": st.column_config.NumberColumn("Distance", format="%.2f km"),
                    "HI_RUN": st.column_config.NumberColumn("HI m", format="%d m"),
                    "SPRINTING": st.column_config.NumberColumn("Sprint m", format="%d m"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
                }
            )
