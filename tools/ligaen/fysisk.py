import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONSTANTER & MAPPING ---
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"
EXCLUDE_LIST = ["114516", "570705", "624707", "523647", "39664"] 

KLUB_NAVNE = {
    "HVI": "Hvidovre IF",
    "KIF": "Kolding IF",
    "MID": "Middelfart",
    "HIK": "Hobro IK",
    "LBK": "Lyngby BK",
    "B93": "B.93",
    "ARF": "Aarhus Fremad",
    "ACH": "Horsens",
    "HBK": "HB Køge",
    "EFB": "Esbjerg fB",
    "HIL": "Hillerød",
}

def get_opponent_name(description):
    """Udtrækker modstandernavn fra 'HVI - MOD' eller 'MOD - HVI'."""
    if not description or ' - ' not in description:
        return "Ukendt"
    teams = [t.strip() for t in description.split(' - ')]
    # Find den kode der ikke er HVI
    opp_code = teams[1] if teams[0] == 'HVI' else teams[0]
    return KLUB_NAVNE.get(opp_code, opp_code)

def vis_side(conn, name_map=None):
    # --- 1. HENT LOKAL MAPPING ---
    df_local = load_local_players()
    player_mapping = {}
    if df_local is not None and not df_local.empty:
        df_local.columns = [c.strip() for c in df_local.columns]
        if 'optaId' in df_local.columns and 'NAVN' in df_local.columns:
            df_local['optaId'] = df_local['optaId'].astype(str).split('.').str[0].str.strip()
            player_mapping = df_local.set_index('optaId')['NAVN'].to_dict()

    # --- 2. HENT DATA ---
    @st.cache_data(ttl=600)
    def get_safe_data():
        today = datetime.now().strftime('%Y-%m-%d')
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

    t1, t2, t3, t4 = st.tabs(["Hvidovre IF", "Graf", "Top 5-oversigt", "Kampoversigt"])

    # --- TAB 1: P90 ---
    with t1:
        df_hif = df_phys[df_phys['Hold'] == "Hvidovre IF"].copy()
        summary = df_hif.groupby('DISPLAY_NAME').agg({
            'MINS_DECIMAL': 'sum', 'DISTANCE': 'sum', 'HI_RUN': 'sum', 
            'SPRINTING': 'sum', 'TOP_SPEED': 'max', 'NO_OF_HIGH_INTENSITY_RUNS': 'sum'
        }).reset_index()

        summary = summary[summary['MINS_DECIMAL'] > 15].copy()
        summary['Dist_P90'] = (summary['DISTANCE'] / summary['MINS_DECIMAL']) * 90 / 1000
        summary['HI_P90'] = (summary['HI_RUN'] / summary['MINS_DECIMAL']) * 90
        summary['Sprint_P90'] = (summary['SPRINTING'] / summary['MINS_DECIMAL']) * 90
        summary['HIR_Actions_P90'] = (summary['NO_OF_HIGH_INTENSITY_RUNS'] / summary['MINS_DECIMAL']) * 90
        
        plot_df = summary.sort_values('Dist_P90', ascending=False)
        st.dataframe(
            plot_df, 
            column_config={
                "DISPLAY_NAME": st.column_config.TextColumn("Spiller", width="medium"),
                "Dist_P90": st.column_config.NumberColumn("KM/90", format="%.2f km"),
                "HI_P90": st.column_config.NumberColumn("HI m/90", format="%d m"),
                "Sprint_P90": st.column_config.NumberColumn("Sprint/90", format="%d m"),
                "HIR_Actions_P90": st.column_config.NumberColumn("HI Akt.", format="%.2f"),
                "TOP_SPEED": st.column_config.NumberColumn("Top", format="%.2f km/t")
            },
            column_order=("DISPLAY_NAME", "Dist_P90", "HI_P90", "Sprint_P90", "HIR_Actions_P90", "TOP_SPEED"),
            use_container_width=True, hide_index=True, height=(len(plot_df)+1)*35+45
        )

    # --- TAB 2: GRAF ---
    with t2:
        kat_map = {"Dist_P90": "KM pr. 90", "HI_P90": "HI m pr. 90", "Sprint_P90": "Sprint pr. 90", "HIR_Actions_P90": "HI Aktioner P90", "TOP_SPEED": "Topfart km/t"}
        valg = st.selectbox("Vælg kategori", list(kat_map.keys()), format_func=lambda x: kat_map[x])
        plot_df_sorted = summary.sort_values(valg, ascending=False)
        
        fig = px.bar(plot_df_sorted, x='DISPLAY_NAME', y=valg, text_auto='.2f', color=valg, color_continuous_scale='reds', title=f"Hvidovre IF: {kat_map[valg]}")
        fig.update_traces(hovertemplate=f"<b>%{{x}}</b><br>{kat_map[valg]}: %{{y:.2f}}<extra></extra>")
        fig.update_yaxes(range=[plot_df_sorted[valg].min()*0.8, plot_df_sorted[valg].max()*1.05], visible=False, showgrid=False)
        fig.update_layout(xaxis_tickangle=-45, xaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 3: TOP 5 ---
    with t3:
        st.subheader("Fysiske Top-præstationer (Alle spillere)")
        c1, c2, c3 = st.columns(3)
        
        def process_top5(metric, ascending=False):
            df = df_phys.nlargest(5, metric)[['DISPLAY_NAME', 'MATCH_SSIID', 'Hold', metric]].copy()
            df = df.merge(df_meta[['MATCH_SSIID', 'DESCRIPTION']], on='MATCH_SSIID', how='left')
            df['Klub'] = df.apply(lambda r: 'Hvidovre IF' if r['Hold'] == 'Hvidovre IF' else get_opponent_name(r['DESCRIPTION']), axis=1)
            return df

        with c1:
            st.write("**Topfart (km/t)**")
            df1 = process_top5('TOP_SPEED')
            st.dataframe(df1[['DISPLAY_NAME', 'Klub', 'TOP_SPEED']], column_config={"TOP_SPEED": st.column_config.NumberColumn("Km/t", format="%.2f km/t")}, use_container_width=True, hide_index=True)
            
        with c2:
            st.write("**HI løb i én kamp (m)**")
            df2 = process_top5('HI_RUN')
            st.dataframe(df2[['DISPLAY_NAME', 'Klub', 'HI_RUN']], column_config={"HI_RUN": st.column_config.NumberColumn("Meter", format="%d m")}, use_container_width=True, hide_index=True)

        with c3:
            st.write("**Sprint i én kamp (m)**")
            df3 = process_top5('SPRINTING')
            st.dataframe(df3[['DISPLAY_NAME', 'Klub', 'SPRINTING']], column_config={"SPRINTING": st.column_config.NumberColumn("Meter", format="%d m")}, use_container_width=True, hide_index=True)

    # --- TAB 4: KAMPOVERSIGT ---
    with t4:
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt_kamp = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique())
            kamp_info = df_hif_matches[df_hif_matches['LABEL'] == valgt_kamp].iloc[0]
            opp_name = get_opponent_name(kamp_info['DESCRIPTION'])
            
            df_m = df_phys[df_phys['MATCH_SSIID'] == kamp_info['MATCH_SSIID']].copy()
            df_m['KM'] = df_m['DISTANCE'] / 1000
            df_m['Klub'] = df_m['Hold'].apply(lambda x: 'Hvidovre IF' if x == 'Hvidovre IF' else opp_name)
            
            st.dataframe(
                df_m.sort_values(by='DISTANCE', ascending=False), 
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
                use_container_width=True, hide_index=True, height=calc_height_m  # Fjerner scrollbar ved at tvinge højden ud
            )
