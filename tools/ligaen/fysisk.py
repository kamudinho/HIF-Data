import streamlit as st
import pandas as pd

HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    # --- TRIN 1: METADATA ---
    @st.cache_data(ttl=600)
    def get_matches():
        # Vi bruger kolonnenavne direkte fra dit dump: STARTTIME, MATCH_SSIID osv.
        query = f"""
        SELECT 
            TRIM(MATCH_SSIID) as MATCH_SSIID,
            STARTTIME,
            HOME_SSIID,
            AWAY_SSIID,
            HOMEOPTA_UUID,
            AWAY_OPTAUUID,
            HOME_SCORE,
            AWAY_SCORE
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
        WHERE (HOMEOPTA_UUID = '{HIF_OPTA_UUID}' OR AWAY_OPTAUUID = '{HIF_OPTA_UUID}')
        ORDER BY STARTTIME DESC
        LIMIT 25
        """
        return conn.query(query)

    df_meta = get_matches()

    if df_meta.empty:
        st.warning("Ingen kampe fundet i Metadata.")
        return

    # Fix: Sørg for at konvertere til datetime før vi bruger .dt
    df_meta['STARTTIME'] = pd.to_datetime(df_meta['STARTTIME'])

    # Lav labels (Nu bruger vi kun STARTTIME kolonnen som findes)
    df_meta['LABEL'] = (
        df_meta['STARTTIME'].dt.strftime('%d/%m-%Y') + 
        " | " + df_meta['HOME_SCORE'].astype(str) + " - " + df_meta['AWAY_SCORE'].astype(str)
    )
    
    valgt_label = st.selectbox("Vælg Kamp:", df_meta['LABEL'].unique())
    # Find den række der matcher det valgte label
    m = df_meta[df_meta['LABEL'] == valgt_label].iloc[0]
    valgt_ssiid = m['MATCH_SSIID']

    # --- TRIN 2: TEAM DATA ---
    @st.cache_data(ttl=600)
    def get_team_stats(ssiid):
        return conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM WHERE TRIM(MATCH_SSIID) = '{ssiid}'")

    df_teams = get_team_stats(valgt_ssiid)

    if df_teams.empty:
        st.info(f"Metadata fundet for kampen, men fysiske hold-data (F53A) mangler for ID: {valgt_ssiid[:6]}")
        return

    # Vis hold-distancer
    st.write("---")
    hif_id = m['HOME_SSIID'] if m['HOMEOPTA_UUID'] == HIF_OPTA_UUID else m['AWAY_SSIID']
    
    c1, c2 = st.columns(2)
    for _, row in df_teams.iterrows():
        is_hif = (str(row['TEAM_SSIID']) == str(hif_id))
        with (c1 if is_hif else c2):
            st.metric(row['TEAM_NAME'], f"{row['TEAMDISTANCE']/1000:.2f} km")
            st.caption("Hvidovre IF" if is_hif else "Modstander")

    # --- TRIN 3: PLAYER DATA ---
    @st.cache_data(ttl=300)
    def get_player_stats(ssiid):
        return conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE TRIM(MATCH_SSIID) = '{ssiid}'")

    df_players = get_player_stats(valgt_ssiid)

    if not df_players.empty:
        st.write("---")
        df_players['NAVNE'] = df_players['PLAYER_SSIID'].map(name_map).fillna(df_players['PLAYER_NAME'])
        
        t_navne = df_teams['TEAM_NAME'].unique().tolist()
        valgt_hold = st.radio("Vis spillere for:", t_navne, horizontal=True)
        
        target_team_id = df_teams[df_teams['TEAM_NAME'] == valgt_hold]['TEAM_SSIID'].iloc[0]
        df_vis = df_players[df_players['TEAM_SSIID'] == target_team_id].copy()

        st.dataframe(
            df_vis[['NAVNE', 'DISTANCE', 'TOP_SPEED', 'SPRINTS']].sort_values('DISTANCE', ascending=False),
            column_config={
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%.0f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/h")
            },
            use_container_width=True, hide_index=True
        )
