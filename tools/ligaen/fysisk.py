import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    # --- INDLÆS SPILLERDATA FRA CSV ---
    @st.cache_data
    def load_player_mapping():
        try:
            # Vi prøver at detektere om der bruges ; eller ,
            df_map = pd.read_csv("data/players.csv", sep=None, engine='python')
            
            # Rens kolonnenavne for eventuelle usynlige mellemrum
            df_map.columns = df_map.columns.str.strip()
            
            # Sikr at optaId er tekst og fjern dubletter
            df_map['optaId'] = df_map['optaId'].astype(str).str.strip()
            
            return df_map.set_index('optaId')['NAVN'].to_dict()
        except Exception as e:
            st.error(f"Fejl ved indlæsning af CSV: {e}")
            return {}
            
    @st.cache_data(ttl=600)
    def get_safe_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
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

        query_phys = f"""
        SELECT 
            p.MATCH_SSIID, p.PLAYER_NAME, p."optaId", p.MINUTES, 
            p.DISTANCE, p."HIGH SPEED RUNNING", p."SPRINTING", p."TOP_SPEED",
            p."NO_OF_HIGH_INTENSITY_RUNS"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE p.MATCH_SSIID IN (SELECT MATCH_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA WHERE "DATE" >= '2025-07-01')
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

    # Mapper DISPLAY_NAME og Hold baseret på players.csv
    def map_info(row):
        oid = str(row['optaId'])
        if oid in player_mapping:
            return player_mapping[oid], 'Hvidovre IF'
        return row['PLAYER_NAME'], 'Modstander'

    df_phys[['DISPLAY_NAME', 'Hold']] = df_phys.apply(
        lambda x: pd.Series(map_info(x)), axis=1
    )

    t1, t2, t3, t4 = st.tabs(["Hvidovre IF (P90)", "Analyse & Grafer", "Liga Top 5", "Kampoversigt"])

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
        summary['Dist_P90'] = round((summary['DISTANCE'] / summary['MINS_DECIMAL']) * 90 / 1000, 2)
        summary['HI_P90'] = round((summary['HI_RUN'] / summary['MINS_DECIMAL']) * 90, 0)
        summary['Sprint_P90'] = round((summary['SPRINTING'] / summary['MINS_DECIMAL']) * 90, 0)
        summary['HIR_Actions_P90'] = round((summary['NO_OF_HIGH_INTENSITY_RUNS'] / summary['MINS_DECIMAL']) * 90, 1)

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

    with t2:
        st.subheader("Visuel Sammenligning (Hvidovre IF)")
        kat_mapping = {
            "Dist_P90": "KM pr. 90", "HI_P90": "HI m pr. 90", 
            "Sprint_P90": "Sprint pr. 90", "HIR_Actions_P90": "HI Aktioner pr. 90", 
            "TOP_SPEED": "Topfart km/t"
        }
        kat_valg = st.selectbox("Vælg kategori", list(kat_mapping.keys()), format_func=lambda x: kat_mapping[x])
        
        plot_df = summary.sort_values(kat_valg, ascending=False)
        fig = px.bar(plot_df, x='DISPLAY_NAME', y=kat_valg, text=kat_valg,
                     color=kat_valg, color_continuous_scale='Blues')
        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with t3:
        st.subheader("Liga Top 5")
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
            df_match['KM'] = round(df_match['DISTANCE'] / 1000, 2)
            df_match = df_match.sort_values(by=['Hold', 'DISTANCE'], ascending=[False, False])
            
            st.dataframe(
                df_match[['DISPLAY_NAME', 'Hold', 'MINUTES', 'KM', 'HI_RUN', 'SPRINTING', 'TOP_SPEED']], 
                use_container_width=True, hide_index=True
            )
