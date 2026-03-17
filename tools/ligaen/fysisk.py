import streamlit as st
import pandas as pd
from datetime import datetime

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_safe_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Hent Metadata (Uændret - bruges til kampvælgeren)
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

        # 2. Hent Fysisk Data med præcis Hold-identifikation via JSON Metadata
        # Vi bruger en CTE (WITH) til at flade HOME_PLAYERS arrayet ud
        query_phys = f"""
        WITH hvidovre_ids AS (
            SELECT DISTINCT 
                m.MATCH_SSIID,
                f.value:"optaId"::string AS opta_id
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m,
            LATERAL FLATTEN(input => m.HOME_PLAYERS) f
            WHERE m.HOME_SSIID = '{HIF_SSIID}'
        )
        SELECT 
            p.MATCH_SSIID, 
            p.PLAYER_NAME, 
            p."optaId",
            p.MINUTES, 
            p.DISTANCE, 
            p."HIGH SPEED RUNNING", 
            p."SPRINTING", 
            p."TOP_SPEED",
            CASE 
                WHEN h.opta_id IS NOT NULL THEN 'Hvidovre IF'
                ELSE 'Modstander'
            END AS "Hold"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        LEFT JOIN hvidovre_ids h 
            ON p.MATCH_SSIID = h.MATCH_SSIID 
            AND p."optaId" = h.opta_id
        WHERE p.MATCH_SSIID IN (
            SELECT MATCH_SSIID 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA 
            WHERE "DATE" >= '2025-07-01'
        )
        """
        df_phys = conn.query(query_phys)
        return df_meta, df_phys

    df_meta, df_phys = get_safe_data()

    if df_phys.empty:
        st.error("Kunne ikke hente data. Tjek Snowflake-forbindelsen.")
        return

    # --- DATABEHANDLING ---
    def parse_minutes(val):
        try:
            val_str = str(val)
            if ':' in val_str:
                m, s = map(int, val_str.split(':'))
                return round(m + s/60, 1)
            return float(val)
        except: return 0.0

    df_phys['MINS_DECIMAL'] = df_phys['MINUTES'].apply(parse_minutes)
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'] + df_phys['SPRINTING']

    # Vi behøver ikke længere 'appearance_count' logikken, 
    # da 'Hold' kolonnen kommer direkte og korrekt fra SQL!

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # Sæson-total (Kun HIF)
        df_hif = df_phys[df_phys['Hold'] == "Hvidovre IF"].copy()
        
        summary = df_hif.groupby('PLAYER_NAME').agg({
            'MATCH_SSIID': 'nunique',
            'MINS_DECIMAL': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'TOP_SPEED': 'max'
        }).reset_index().sort_values('DISTANCE', ascending=False)

        st.dataframe(
            summary, 
            column_config={
                "PLAYER_NAME": "Spiller",
                "MATCH_SSIID": "Kampe",
                "MINS_DECIMAL": st.column_config.NumberColumn("Min.", format="%d"),
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%d"),
                "HI_RUN": st.column_config.NumberColumn("HI Meter", format="%d"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            use_container_width=True, hide_index=True
        )

    with t2:
        # Liga Top 5 (Alle kampe efter 1/7)
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_phys.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_phys.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        # Kampvælger (Kun kampe hvor Hvidovre er med)
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique(), label_visibility="collapsed")
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
            df_match = df_match.sort_values(by=['Hold', 'DISTANCE'], ascending=[False, False])
            
            # Vi definerer de kolonner vi vil se, med MATCH_SSIID først
            vis_kolonner = ['MATCH_SSIID', 'PLAYER_NAME', 'Hold', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']
            
            st.dataframe(
                df_match[vis_kolonner], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "MATCH_SSIID": st.column_config.TextColumn("Match ID", width="medium"),
                    "PLAYER_NAME": "Spiller"
                },
                height=(len(df_match) + 1) * 35 + 5
            )
