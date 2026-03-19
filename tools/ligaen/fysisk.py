import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"
EXCLUDE_LIST = ["114516", "570705", "624707", "523647", "39664"] 

def vis_side(conn, name_map=None):
    # --- 1. HENT LOKAL MAPPING ---
    df_local = load_local_players()
    player_mapping = {}
    if df_local is not None and not df_local.empty:
        df_local.columns = [c.strip() for c in df_local.columns]
        if 'optaId' in df_local.columns and 'NAVN' in df_local.columns:
            df_local['optaId'] = df_local['optaId'].astype(str).str.split('.').str[0].str.strip()
            player_mapping = df_local.set_index('optaId')['NAVN'].to_dict()

    # --- 2. HENT DATA ---
    @st.cache_data(ttl=600)
    def get_safe_data():
        today = datetime.now().strftime('%Y-%m-%d')
        # Henter metadata og fysisk data
        query_meta = f"""
        SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND "DATE" >= '2025-07-01' AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
        """
        df_meta = conn.query(query_meta)
        
        query_phys = f"""
        WITH hvidovre_ids AS (
            SELECT DISTINCT m.MATCH_SSIID, f.value:"optaId"::string AS opta_id
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m,
            LATERAL FLATTEN(input => CASE WHEN m.HOME_SSIID = '{HIF_SSIID}' THEN m.HOME_PLAYERS ELSE m.AWAY_PLAYERS END) f
            WHERE m.HOME_SSIID = '{HIF_SSIID}' OR m.AWAY_SSIID = '{HIF_SSIID}'
        )
        SELECT p.MATCH_SSIID, p.PLAYER_NAME, p."optaId", p.MINUTES, p.DISTANCE, 
               p."HIGH SPEED RUNNING", p."SPRINTING", p."TOP_SPEED", p."NO_OF_HIGH_INTENSITY_RUNS",
               CASE WHEN h.opta_id IS NOT NULL THEN 'Hvidovre IF' ELSE 'Modstander' END AS "Hold"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        LEFT JOIN hvidovre_ids h ON p.MATCH_SSIID = h.MATCH_SSIID AND p."optaId" = h.opta_id
        WHERE p.MATCH_SSIID IN (SELECT MATCH_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA WHERE "DATE" >= '2025-07-01')
        """
        return df_meta, conn.query(query_phys)

    df_meta, df_phys = get_safe_data()
    if df_phys.empty:
        st.error("Ingen data fundet.")
        return

    # --- 3. DATABEHANDLING ---
    def parse_minutes(val):
        try:
            v = str(val)
            if ':' in v:
                m, s = map(int, v.split(':'))
                return round(m + s/60, 2)
            return float(val)
        except: return 0.0

    df_phys['MINS_DECIMAL'] = df_phys['MINUTES'].apply(parse_minutes)
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'] + df_phys['SPRINTING']
    df_phys = df_phys[~df_phys['optaId'].astype(str).str.split('.').str[0].isin(EXCLUDE_LIST)].copy()
    df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: player_mapping.get(str(r['optaId']).strip(), r['PLAYER_NAME']), axis=1)

    # --- 4. TABS ---
    t1, t2, t3, t4 = st.tabs(["Hvidovre IF", "Graf", "Top 5-oversigt", "Kampoversigt"])

    # ... Tab 1 og 2 forbliver uændrede ...

    # --- TAB 3: Top 5-oversigt ---
    with t3:
        st.subheader("Fysiske Top-præstationer (Alle spillere)")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.write("**Topfart (km/t)**")
            # Finder top 5 og samler med metadata for at få klubnavn
            top_speed_df = df_phys.nlargest(5, 'TOP_SPEED')[['DISPLAY_NAME', 'MATCH_SSIID', 'Hold', 'TOP_SPEED']]
            top_speed_df = top_speed_df.merge(df_meta[['MATCH_SSIID', 'DESCRIPTION']], on='MATCH_SSIID', how='left')
            
            # Oversætter "Modstander" til klubnavn baseret på DESCRIPTION (f.eks. "HIF - KIF")
            def map_opp_name_top5(row):
                if row['Hold'] == 'Modstander' and pd.notna(row['DESCRIPTION']):
                    teams = row['DESCRIPTION'].split(' - ')
                    return teams[0] if teams[0] != 'HIF' else teams[1]
                return row['Hold']

            top_speed_df['Klub'] = top_speed_df.apply(map_opp_name_top5, axis=1)

            st.dataframe(
                top_speed_df[['DISPLAY_NAME', 'Klub', 'TOP_SPEED']],
                column_config={
                    "DISPLAY_NAME": st.column_config.TextColumn("Spiller", width="medium"),
                    "Klub": st.column_config.TextColumn("Klub", width="small"),
                    "TOP_SPEED": st.column_config.NumberColumn("Km/t", format="%.2f km/t")
                },
                use_container_width=True, hide_index=True
            )
            
        with c2:
            st.write("**HI løb i én kamp (m)**")
            hi_run_df = df_phys.nlargest(5, 'HI_RUN')[['DISPLAY_NAME', 'MATCH_SSIID', 'Hold', 'HI_RUN']].copy()
            hi_run_df = hi_run_df.merge(df_meta[['MATCH_SSIID', 'DESCRIPTION']], on='MATCH_SSIID', how='left')
            hi_run_df['Klub'] = hi_run_df.apply(map_opp_name_top5, axis=1)
            hi_run_df['HI_RUN'] = hi_run_df['HI_RUN'].round(0) 
            
            st.dataframe(
                hi_run_df[['DISPLAY_NAME', 'Klub', 'HI_RUN']],
                column_config={
                    "DISPLAY_NAME": st.column_config.TextColumn("Spiller", width="medium"),
                    "Klub": st.column_config.TextColumn("Klub", width="small"),
                    "HI_RUN": st.column_config.NumberColumn("Meter", format="%d m")
                },
                use_container_width=True, hide_index=True
            )

        with c3:
            st.write("**Sprint i én kamp (m)**")
            # Ændret den tredje kolonne til Sprint for at give mere værdi
            sprint_df = df_phys.nlargest(5, 'SPRINTING')[['DISPLAY_NAME', 'MATCH_SSIID', 'Hold', 'SPRINTING']].copy()
            sprint_df = sprint_df.merge(df_meta[['MATCH_SSIID', 'DESCRIPTION']], on='MATCH_SSIID', how='left')
            sprint_df['Klub'] = sprint_df.apply(map_opp_name_top5, axis=1)
            sprint_df['SPRINTING'] = sprint_df['SPRINTING'].round(0)
            
            st.dataframe(
                sprint_df[['DISPLAY_NAME', 'Klub', 'SPRINTING']],
                column_config={
                    "DISPLAY_NAME": st.column_config.TextColumn("Spiller", width="medium"),
                    "Klub": st.column_config.TextColumn("Klub", width="small"),
                    "SPRINTING": st.column_config.NumberColumn("Meter", format="%d m")
                },
                use_container_width=True, hide_index=True
            )

    # --- TAB 4: Kampoversigt ---
    with t4:
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt_kamp = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique())
            kamp_info = df_hif_matches[df_hif_matches['LABEL'] == valgt_kamp].iloc[0]
            m_id = kamp_info['MATCH_SSIID']
            
            # Find modstanderens navn fra DESCRIPTION (f.eks. "HIF - KIF")
            teams = kamp_info['DESCRIPTION'].split(' - ')
            modstander_navn = teams[0] if teams[0] != 'HIF' else teams[1]
            
            df_m = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
            df_m['KM'] = df_m['DISTANCE'] / 1000
            
            # Oversætter "Modstander" til det specifikke holdnavn
            df_m['Klub'] = df_m['Hold'].apply(lambda x: 'Hvidovre IF' if x == 'Hvidovre IF' else modstander_navn)
            
            match_plot = df_m.sort_values(by='DISTANCE', ascending=False)
            calc_height_m = (len(match_plot) + 1) * 35 + 45

            st.dataframe(
                match_plot, 
                column_config={
                    "DISPLAY_NAME": st.column_config.TextColumn("Spiller", width="medium"),
                    "Klub": st.column_config.TextColumn("Klub", width="small"),
                    "MINUTES": st.column_config.TextColumn("Min"), 
                    "KM": st.column_config.NumberColumn("KM", format="%.2f km"),
                    "HI_RUN": st.column_config.NumberColumn("HI m", format="%d m"),
                    "SPRINTING": st.column_config.NumberColumn("Sprint m", format="%d m"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.2f km/t")
                },
                column_order=("DISPLAY_NAME", "Klub", "MINUTES", "KM", "HI_RUN", "SPRINTING", "TOP_SPEED"),
                use_container_width=True, hide_index=True, height=calc_height_m
            )
