import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
# Vi henter din eksisterende indlæser
from data.data_load import load_local_players 

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    # --- 1. HENT MAPPING FRA DIN CSV ---
    # Vi henter rå-dataen uden at tvinge store bogstaver i denne funktion
    df_local = load_local_players()
    player_mapping = {}
    
    if df_local is not None and not df_local.empty:
        # Vi sikrer os, at vi bruger de præcise kolonnenavne fra din CSV
        # Vi fjerner eventuelle mellemrum i kolonnenavnene for en sikkerheds skyld
        df_local.columns = [c.strip() for c in df_local.columns]
        
        if 'optaId' in df_local.columns and 'NAVN' in df_local.columns:
            # Konverter ID til string og rens for .0 (hvis Excel har gemt som float)
            df_local['optaId'] = df_local['optaId'].astype(str).str.split('.').str[0].str.strip()
            # Lav ordbogen: { "544954": "A. Iljazovski" }
            player_mapping = df_local.set_index('optaId')['NAVN'].to_dict()

    # --- 2. HENT DATA FRA SNOWFLAKE ---
    @st.cache_data(ttl=600)
    def get_physical_data():
        # Her bruger vi det præcise kolonnenavn p."optaId" med anførselstegn 
        # for at respektere casingen i Snowflake
        query_phys = f"""
        SELECT 
            p.MATCH_SSIID, 
            p.PLAYER_NAME, 
            p."optaId", 
            p.MINUTES, 
            p.DISTANCE, 
            p."HIGH SPEED RUNNING", 
            p."SPRINTING", 
            p."TOP_SPEED",
            p."NO_OF_HIGH_INTENSITY_RUNS"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE p.MATCH_SSIID IN (
            SELECT MATCH_SSIID 
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA 
            WHERE "DATE" >= '2025-07-01'
        )
        """
        return conn.query(query_phys)

    df_phys = get_physical_data()

    if df_phys is None or df_phys.empty:
        st.error("Kunne ikke hente fysisk data fra Snowflake.")
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

    # Mapping funktion
    def map_hif_players(row):
        # Snowflake p."optaId" skal matche CSV optaId
        oid = str(row['optaId']).strip()
        if oid in player_mapping:
            return player_mapping[oid], 'Hvidovre IF'
        return row['PLAYER_NAME'], 'Modstander'

    # Anvend navne-mapping og hold-identifikation
    df_phys[['DISPLAY_NAME', 'Hold']] = df_phys.apply(
        lambda x: pd.Series(map_hif_players(x)), axis=1
    )

    # --- 4. VISNING (TABS) ---
    st.title("Fysisk Performance - Hvidovre IF")
    
    t1, t2, t3 = st.tabs(["Hvidovre IF (P90)", "Analyse & Grafer", "Debug / Tjek Match"])

    with t1:
        df_hif = df_phys[df_phys['Hold'] == "Hvidovre IF"].copy()
        
        if not df_hif.empty:
            summary = df_hif.groupby('DISPLAY_NAME').agg({
                'MINS_DECIMAL': 'sum',
                'DISTANCE': 'sum',
                'HI_RUN': 'sum',
                'SPRINTING': 'sum',
                'TOP_SPEED': 'max',
                'NO_OF_HIGH_INTENSITY_RUNS': 'sum'
            }).reset_index()

            # Beregn P90 for relevante spillere (over 15 min totalt)
            summary = summary[summary['MINS_DECIMAL'] > 15].copy()
            summary['Dist_P90'] = (summary['DISTANCE'] / summary['MINS_DECIMAL']) * 90 / 1000
            summary['HI_P90'] = (summary['HI_RUN'] / summary['MINS_DECIMAL']) * 90
            summary['Sprint_P90'] = (summary['SPRINTING'] / summary['MINS_DECIMAL']) * 90
            summary['HI_Actions_P90'] = (summary['NO_OF_HIGH_INTENSITY_RUNS'] / summary['MINS_DECIMAL']) * 90

            st.dataframe(
                summary.sort_values('Dist_P90', ascending=False),
                column_config={
                    "DISPLAY_NAME": "Spiller",
                    "Dist_P90": st.column_config.NumberColumn("KM pr. 90", format="%.2f km"),
                    "HI_P90": st.column_config.NumberColumn("HI m pr. 90", format="%d m"),
                    "Sprint_P90": st.column_config.NumberColumn("Sprint pr. 90", format="%d m"),
                    "HI_Actions_P90": st.column_config.NumberColumn("HI Akt. P90", format="%.1f"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t"),
                    "MINS_DECIMAL": "Minutter"
                },
                hide_index=True, use_container_width=True
            )
        else:
            st.warning("Ingen spillere matchede din players.csv.")

    with t2:
        if not df_hif.empty:
            st.subheader("Visuel Sammenligning")
            kat_mapping = {
                "Dist_P90": "KM pr. 90", "HI_P90": "HI m pr. 90", 
                "Sprint_P90": "Sprint pr. 90", "HI_Actions_P90": "HI Aktioner pr. 90", 
                "TOP_SPEED": "Topfart km/t"
            }
            kat_valg = st.selectbox("Vælg kategori", list(kat_mapping.keys()), format_func=lambda x: kat_mapping[x])
            
            plot_df = summary.sort_values(kat_valg, ascending=False)
            fig = px.bar(plot_df, x='DISPLAY_NAME', y=kat_valg, text=kat_valg,
                         color=kat_valg, color_continuous_scale='Blues')
            fig.update_traces(textposition='outside', texttemplate='%{text:.1f}')
            fig.update_layout(xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with t3:
        st.subheader("Debug Center")
        st.write("Her kan du se om IDs i Snowflake matcher din CSV:")
        
        # Vis de unikke parringer vi har i databasen lige nu
        db_debug = df_phys[['PLAYER_NAME', 'optaId', 'Hold']].drop_duplicates()
        st.dataframe(db_debug.sort_values('Hold', ascending=False))
        
        # Vis din CSV mapping
        st.write("Din CSV mapping (optaId -> NAVN):")
        st.json(player_mapping)
