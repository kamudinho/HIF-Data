import streamlit as st
import pandas as pd
import plotly.express as px
import json
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
        try:
            m = float(meter)
            if m < 1000: return f"{int(m)} m"
            else: return f"{m/1000:.2f} km"
        except: return "0 m"

    # --- 3. DATA LOAD ---
    @st.cache_data(ttl=600)
    def get_phys_data(ssid):
        sql = f"""
        WITH team_player_ids AS (
            SELECT DISTINCT m.MATCH_SSIID, m.HOME_SSIID, m.AWAY_SSIID,
            f.value:"optaId"::string AS player_opta_id
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m,
            LATERAL FLATTEN(input => CASE WHEN m.HOME_SSIID = '{ssid}' THEN m.HOME_PLAYERS ELSE m.AWAY_PLAYERS END) f
            WHERE m.HOME_SSIID = '{ssid}' OR m.AWAY_SSIID = '{ssid}'
        )
        SELECT p.*, h.player_opta_id, h.HOME_SSIID, h.AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        INNER JOIN team_player_ids h ON p.MATCH_SSIID = h.MATCH_SSIID AND p."optaId" = h.player_opta_id
        WHERE p.MATCH_DATE >= '2025-07-01'
        """
        return conn.query(sql)

    df_phys = get_phys_data(v_ssid)
    df_phys.columns = [c.upper() for c in df_phys.columns]

    df_local = load_local_players()
    p_map = {}
    if df_local is not None:
        oid_col = next((c for c in df_local.columns if c.lower() == 'optaid'), 'optaId')
        df_local['clean_oid'] = df_local[oid_col].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "0")
        p_map = df_local.set_index('clean_oid')['NAVN'].to_dict()

    # --- 4. TABS ---
    t1, t2, t3, t4, t5 = st.tabs([f"{valgt_hold}-oversigt", "Graf", "Scatterplot", "Top 5", "Kampanalyse"])

    if not df_phys.empty:
        df_phys['MINS_DEC'] = df_phys['MINUTES'].apply(parse_to_mins)
        df_phys['HI_TOTAL'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
        df_phys['DISPLAY_NAME'] = df_phys.apply(lambda r: p_map.get(str(r['PLAYER_OPTA_ID']), r['PLAYER_NAME']), axis=1)

        summary = df_phys.groupby('DISPLAY_NAME').agg({
            'MINS_DEC': 'sum', 'DISTANCE': 'sum', 'HI_TOTAL': 'sum', 'TOP_SPEED': 'max',
            'HIGH SPEED RUNNING': 'sum', 'SPRINTING': 'sum'
        }).reset_index()
        summary = summary[summary['MINS_DEC'] > 5].copy()

        with t1:
            summary['KM_TOTAL_NUM'] = summary['DISTANCE'] / 1000
            summary['KM90_NUM'] = (summary['KM_TOTAL_NUM'] / summary['MINS_DEC']) * 90
            summary['Total Distance'] = summary['DISTANCE'].apply(format_smart_dist)
            summary['KM/90'] = summary['KM90_NUM'].apply(lambda x: f"{x:.2f} km")
            summary['HI pr. 90'] = ((summary['HI_TOTAL'] / summary['MINS_DEC']) * 90).apply(lambda x: f"{int(x)} m")

            st.dataframe(
                summary[['DISPLAY_NAME', 'MINS_DEC', 'Total Distance', 'KM/90', 'HI pr. 90', 'TOP_SPEED', 'KM_TOTAL_NUM']].sort_values('KM_TOTAL_NUM', ascending=False),
                column_config={
                    "DISPLAY_NAME": "Spiller", 
                    "MINS_DEC": st.column_config.NumberColumn("Minutter", format="%.2f"), 
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t"),
                    "KM_TOTAL_NUM": None
                },
                use_container_width=True, hide_index=True, height=600
            )

        with t2:
            # 1. Definer metrikker og deres foretrukne enhed
            # Format: "Navn": (Kolonne, Skal_omregnes_til_km)
            metrics_config = {
                "Total Distance (km)": ("DISTANCE", True),
                "High Speed Running (m)": ("HIGH SPEED RUNNING", False),
                "Sprinting (m)": ("SPRINTING", False),
                "HI Løb (m)": ("HI_TOTAL", False),
                "Topfart (km/t)": ("TOP_SPEED", False)
            }
            
            valgt_metrik_navn = st.selectbox("Vælg kategori til graf", list(metrics_config.keys()))
            valgt_kolonne, skal_til_km = metrics_config[valgt_metrik_navn]
            
            # 2. Klargør data og sorter
            plot_data = summary.copy()
            
            if skal_til_km:
                plot_data[valgt_kolonne] = plot_data[valgt_kolonne] / 1000
            
            plot_data = plot_data.sort_values(valgt_kolonne, ascending=False)

            # 3. Lav Bar Chart
            fig_bar = px.bar(
                plot_data, 
                x='DISPLAY_NAME', 
                y=valgt_kolonne, 
                text=valgt_kolonne,
                labels={valgt_kolonne: valgt_metrik_navn, 'DISPLAY_NAME': 'Spiller'},
                caption=f"{valgt_metrik_navn} pr. spiller (Sæson total)",
                color_discrete_sequence=[HIF_ROD]
            )

            # 4. Formatering af tekst over søjlerne
            # Distance og Topfart får decimaler, de andre (meter-værdier) vises som hele tal
            if skal_til_km or valgt_kolonne == 'TOP_SPEED':
                t_format = '%{text:.2f}' if skal_til_km else '%{text:.1f}'
            else:
                t_format = '%{text:d}'

            fig_bar.update_traces(
                texttemplate=t_format, 
                textposition='outside', 
                cliponaxis=False
            )
            
            fig_bar.update_layout(
                xaxis_tickangle=-45, 
                height=450,
                yaxis_title=valgt_metrik_navn
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)

        with t3:
            summary['KM90_NUM'] = (summary['DISTANCE'] / 1000 / summary['MINS_DEC']) * 90
            fig = px.scatter(
                summary, x='KM90_NUM', y='TOP_SPEED', text='DISPLAY_NAME',
                labels={'KM90_NUM': 'KM pr. 90 min', 'TOP_SPEED': 'Topfart (km/t)'},
                height=650
            )
            fig.update_traces(textposition='top center', marker=dict(size=8.5, color=HIF_ROD))
            st.plotly_chart(fig, use_container_width=True)

    with t4:
        df_league = conn.query("""
            SELECT PLAYER_NAME, SUM(DISTANCE) as TOTAL_DIST, SUM("HIGH SPEED RUNNING" + SPRINTING) as TOTAL_HI, MAX(TOP_SPEED) as MAX_SPEED,
            SUM(CASE WHEN MINUTES LIKE '%:%' THEN CAST(SPLIT_PART(MINUTES, ':', 1) AS FLOAT) + CAST(SPLIT_PART(MINUTES, ':', 2) AS FLOAT)/60 ELSE CAST(MINUTES AS FLOAT) / 60 END) as TOTAL_MINS
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS GROUP BY PLAYER_NAME HAVING TOTAL_MINS > 90
        """)
        if not df_league.empty:
            df_league['KM90'] = (df_league['TOTAL_DIST'] / 1000 / df_league['TOTAL_MINS']) * 90
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write("**Topfart**")
                st.dataframe(df_league.nlargest(5, 'MAX_SPEED')[['PLAYER_NAME', 'MAX_SPEED']], hide_index=True)
            with c2:
                st.write("**KM pr. 90**")
                st.dataframe(df_league.nlargest(5, 'KM90')[['PLAYER_NAME', 'KM90']].assign(KM90=lambda x: x['KM90'].round(2)), hide_index=True)
            with c3:
                st.write("**HI pr. 90**")
                df_l_hi = df_league.nlargest(5, 'TOTAL_HI').copy()
                df_l_hi['HI/90'] = ((df_l_hi['TOTAL_HI'] / df_l_hi['TOTAL_MINS']) * 90).astype(int)
                st.dataframe(df_l_hi[['PLAYER_NAME', 'HI/90']], hide_index=True)

    with t5:
        df_meta = conn.query(f"""
            SELECT DISTINCT 
                TO_VARCHAR(s."DATE", 'YYYY-MM-DD') as DATE_STR, 
                s.DESCRIPTION, s.MATCH_SSIID, s.HOME_SSIID, s.AWAY_SSIID,
                m.HOME_PLAYERS, m.AWAY_PLAYERS
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA s
            JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m ON s.MATCH_SSIID = m.MATCH_SSIID
            WHERE s.HOME_SSIID = '{v_ssid}' OR s.AWAY_SSIID = '{v_ssid}'
            ORDER BY DATE_STR DESC
        """)
        
        if not df_meta.empty:
            df_meta['LABEL'] = df_meta['DATE_STR'] + " - " + df_meta['DESCRIPTION']
            v_kamp = st.selectbox("Vælg kamp", df_meta['LABEL'].unique())
            m_row = df_meta[df_meta['LABEL'] == v_kamp].iloc[0]
            
            ssid_to_full_name = {str(v['ssid']): k for k, v in TEAMS.items() if 'ssid' in v}
            home_full_name = ssid_to_full_name.get(str(m_row['HOME_SSIID']), "Hjemme")
            away_full_name = ssid_to_full_name.get(str(m_row['AWAY_SSIID']), "Ude")

            df_m = conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_SSIID = '{m_row['MATCH_SSIID']}'")
            
            if not df_m.empty:
                def clean_player_list(plist):
                    if isinstance(plist, str):
                        try: return json.loads(plist)
                        except: return []
                    return plist if isinstance(plist, list) else []

                h_ids = [str(p.get('optaId')) for p in clean_player_list(m_row['HOME_PLAYERS']) if isinstance(p, dict)]
                a_ids = [str(p.get('optaId')) for p in clean_player_list(m_row['AWAY_PLAYERS']) if isinstance(p, dict)]

                df_m['HOLD'] = df_m.apply(lambda r: home_full_name if str(r['optaId']) in h_ids else (away_full_name if str(r['optaId']) in a_ids else "Ukendt"), axis=1)
                df_m['SMART_DIST'] = df_m['DISTANCE'].apply(format_smart_dist)
                df_m['HI_DISP'] = (df_m['HIGH SPEED RUNNING'].fillna(0) + df_m['SPRINTING'].fillna(0)).apply(lambda x: f"{int(x)} m")
                df_m['SPIL'] = df_m.apply(lambda r: p_map.get(str(r['optaId']), r['PLAYER_NAME']), axis=1)
                
                st.dataframe(
                    df_m[['SPIL', 'HOLD', 'MINUTES', 'SMART_DIST', 'HI_DISP', 'TOP_SPEED', 'DISTANCE']].sort_values('DISTANCE', ascending=False),
                    column_config={
                        "SPIL": "Spiller", "HOLD": "Hold", "MINUTES": "Min", "SMART_DIST": "Distance", 
                        "HI_DISP": "HI-løb", "TOP_SPEED": st.column_config.NumberColumn("Top", format="%.1f km/t"), "DISTANCE": None 
                    },
                    use_container_width=True, hide_index=True
                )
