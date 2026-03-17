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
        
        # 1. Hent Metadata
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

        # 2. Hent Fysisk Data med forbedret SQL
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
        st.error("Ingen data fundet.")
        return

    # --- DATABEHANDLING ---
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

    t1, t2, t3 = st.tabs(["📊 Hvidovre IF (P90)", "🏆 Liga Top 5", "⚽ Kampoversigt"])

    with t1:
        st.subheader("Hvidovre IF - Sæsonpræstationer pr. 90 min.")
        df_hif = df_phys[df_phys['Hold'] == "Hvidovre IF"].copy()
        
        # Aggregering
        summary = df_hif.groupby('PLAYER_NAME').agg({
            'MATCH_SSIID': 'nunique',
            'MINS_DECIMAL': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'SPRINTING': 'sum',
            'TOP_SPEED': 'max'
        }).reset_index()

        # Beregn P90 (Kun for spillere med over 15 minutter totalt for at undgå mærkelige outliers)
        summary = summary[summary['MINS_DECIMAL'] > 15].copy()
        summary['Dist_P90'] = (summary['DISTANCE'] / summary['MINS_DECIMAL']) * 90 / 1000 # Nu i KM
        summary['HI_P90'] = (summary['HI_RUN'] / summary['MINS_DECIMAL']) * 90
        summary['Sprint_P90'] = (summary['SPRINTING'] / summary['MINS_DECIMAL']) * 90
        
        # Formatering til visning
        st.dataframe(
            summary.sort_values('Dist_P90', ascending=False), 
            column_config={
                "PLAYER_NAME": "Spiller",
                "MATCH_SSIID": "Kampe",
                "MINS_DECIMAL": st.column_config.NumberColumn("Total Min.", format="%d"),
                "Dist_P90": st.column_config.NumberColumn("KM pr. 90", format="%.2f km"),
                "HI_P90": st.column_config.NumberColumn("HI m pr. 90", format="%d m"),
                "Sprint_P90": st.column_config.NumberColumn("Sprint pr. 90", format="%d m"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            use_container_width=True, hide_index=True
        )

    with t2:
        st.subheader("Ligaens Skarpeste (Top 5)")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.write("**Topfart (km/t)**")
            st.table(df_phys.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5).map(lambda x: f"{x:.1f} km/t"))
            
        with c2:
            st.write("**Total HI Distance (m)**")
            st.table(df_phys.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5).map(lambda x: f"{int(x)} m"))

        with c3:
            st.write("**Total Distance (km)**")
            st.table((df_phys.groupby('PLAYER_NAME')['DISTANCE'].sum() / 1000).nlargest(5).map(lambda x: f"{x:.2f} km"))

    with t3:
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique())
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
            df_match['KM'] = df_match['DISTANCE'] / 1000 # Konverter til KM
            df_match = df_match.sort_values(by=['Hold', 'DISTANCE'], ascending=[False, False])
            
            st.dataframe(
                df_match[['PLAYER_NAME', 'Hold', 'MINUTES', 'KM', 'HI_RUN', 'TOP_SPEED']], 
                use_container_width=True, hide_index=True,
                column_config={
                    "PLAYER_NAME": "Spiller",
                    "KM": st.column_config.NumberColumn("Distance", format="%.2f km"),
                    "HI_RUN": st.column_config.NumberColumn("HI Meter", format="%d m"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
                }
            )
