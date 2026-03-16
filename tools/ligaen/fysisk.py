import streamlit as st
import pandas as pd

# Konstanter baseret på dine værdier
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    st.title("Hvidovre IF | Fysisk Data")

    @st.cache_data(ttl=600)
    def get_unified_data():
        # 1. Find alle Hvidovre-kampe i sæsonen
        query_meta = f"""
        SELECT MATCH_SSIID, DESCRIPTION, "DATE", HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
        ORDER BY "DATE" DESC
        """
        df_meta = conn.query(query_meta)
        if df_meta.empty: return None, None, None
        
        ids = "('" + "','".join(df_meta['MATCH_SSIID'].tolist()) + "')"

        # 2. Hold-performance (Hvidovre vs Modstander)
        query_team = f"""
        SELECT MATCH_SSIID, TEAM_SSIID, TEAM_NAME, TEAMDISTANCE, HIGHSPEEDRUNNING, HIGHSPEEDSPRINTING
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
        WHERE MATCH_SSIID IN {ids}
        """
        df_team = conn.query(query_team)

        # 3. Spiller-detaljer (Den store tabel med alle zoner)
        query_player = f"""
        SELECT 
            MATCH_SSIID, MATCH_TEAMS, PLAYER_NAME, "optaId", 
            MINUTES, DISTANCE, "HIGH SPEED RUNNING", SPRINTING, TOP_SPEED,
            DISTANCE_TIP, DISTANCE_OTIP, DISTANCE_BOP
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID IN {ids}
        """
        df_player = conn.query(query_player)
        
        return df_meta, df_team, df_player

    df_meta, df_team, df_player = get_unified_data()

    if df_meta is None:
        st.warning("Ingen data fundet for Hvidovre IF i 2025/2026.")
        return

    # --- DATAPRÆPARERING ---
    # Konverter MM:SS til decimale minutter for beregninger
    def parse_mins(val):
        try:
            m, s = map(int, val.split(':'))
            return round(m + s/60, 1)
        except: return 0.0

    df_player['MINS_DECIMAL'] = df_player['MINUTES'].apply(parse_mins)
    df_player['HI_DIST'] = df_player['HIGH SPEED RUNNING'] + df_player['SPRINTING']

    # --- SEKTION 1: KAMP OVERBLIK ---
    st.subheader("Hold-sammenligning")
    
    match_options = []
    for _, m in df_meta.iterrows():
        hif = df_team[(df_team['MATCH_SSIID'] == m['MATCH_SSIID']) & (df_team['TEAM_SSIID'] == HIF_SSIID)]
        opp = df_team[(df_team['MATCH_SSIID'] == m['MATCH_SSIID']) & (df_team['TEAM_SSIID'] != HIF_SSIID)]
        
        if not hif.empty:
            match_options.append({
                "id": m['MATCH_SSIID'],
                "label": f"{m['DATE']} | {m['DESCRIPTION']}",
                "hif_dist": hif.iloc[0]['TEAMDISTANCE'],
                "opp_dist": opp.iloc[0]['TEAMDISTANCE'] if not opp.empty else 0
            })

    if match_options:
        df_ov = pd.DataFrame(match_options)
        st.dataframe(
            df_ov[['label', 'hif_dist', 'opp_dist']],
            column_config={
                "label": "Kamp",
                "hif_dist": st.column_config.NumberColumn("HIF (m)", format="%d"),
                "opp_dist": st.column_config.NumberColumn("Modst. (m)", format="%d")
            },
            hide_index=True, use_container_width=True
        )

        # --- SEKTION 2: SPILLER DETALJER ---
        st.divider()
        valgt_id = st.selectbox("Vælg kamp for spiller-dyk:", 
                               options=df_ov['id'].tolist(),
                               format_func=lambda x: next(i['label'] for i in match_options if i['id'] == x))

        # Filtrer spillere på Hvidovre i den valgte kamp
        # (Vi bruger MATCH_TEAMS-tjekket som backup til TEAM_SSIID)
        p_stats = df_player[
            (df_player['MATCH_SSIID'] == valgt_id) & 
            (df_player['MATCH_TEAMS'].str.contains('Hvidovre|HVI', case=False, na=False))
        ].copy()

        st.write("### Spillerpræstationer")
        
        # Tabs for forskellige vinkler
        tab1, tab2 = st.tabs(["Fysiske Totaler", "Bold-kontekst"])
        
        with tab1:
            st.dataframe(
                p_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
                column_config={
                    "PLAYER_NAME": "Spiller",
                    "DISTANCE": st.column_config.NumberColumn("Total (m)", format="%d"),
                    "HI_DIST": "HI Løb (m)",
                    "TOP_SPEED": "Topfart"
                },
                use_container_width=True, hide_index=True
            )

        with tab2:
            st.info("Distance fordelt på boldbesiddelse (TIP = In Possession, OTIP = Out of Possession, BOP = Ball Out of Play)")
            st.dataframe(
                p_stats[['PLAYER_NAME', 'DISTANCE_TIP', 'DISTANCE_OTIP', 'DISTANCE_BOP']].sort_values('DISTANCE_TIP', ascending=False),
                column_config={
                    "DISTANCE_TIP": "Med bold (m)",
                    "DISTANCE_OTIP": "Uden bold (m)",
                    "DISTANCE_BOP": "Bold ude (m)"
                },
                use_container_width=True, hide_index=True
            )

    else:
        st.info("Ingen fysisk data matchet i systemet endnu.")
