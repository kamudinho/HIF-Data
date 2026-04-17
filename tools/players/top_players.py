import streamlit as st

def vis_side(session, valgt_hold_navn):
    # 1. Vi finder lynhurtigt WYID og logo baseret på dit holdvalg
    # Vi bruger din favorit-tabel til at validere holdet
    team_info_query = f"""
        SELECT team_wyid, imagedataurl 
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS 
        WHERE teamname = '{valgt_hold_navn}' 
        LIMIT 1
    """
    team_data = session.sql(team_info_query).to_pandas()
    
    if team_data.empty:
        st.error("Holdet blev ikke fundet i databasen.")
        return

    wyid = team_data.iloc[0]['TEAM_WYID']
    logo_url = team_data.iloc[0]['IMAGEDATAURL']

    # 2. Hent de 5 mest løbestærke spillere
    # Vi bruger WYID direkte i joinen - det er meget mere sikkert!
    query = f"""
    SELECT 
        s.PLAYER_NAME,
        AVG(s.DISTANCE) as DIST, 
        AVG(s."HIGH SPEED RUNNING") as HSR, 
        MAX(s.TOP_SPEED) as SPEED,
        MAX(w.IMAGEDATAURL) as PLAYER_IMG
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS w ON s.optaId = w.OPTAID
    WHERE w.CURRENTTEAM_WYID = {wyid}
    AND s.MATCH_DATE > '2025-07-01'
    GROUP BY s.PLAYER_NAME
    ORDER BY DIST DESC
    LIMIT 5
    """
    
    df = session.sql(query).to_pandas()

    # 3. Visning
    st.image(logo_url, width=100)
    
    for _, row in df.iterrows():
        col1, col2 = st.columns([1, 4])
        with col1:
            st.image(row['PLAYER_IMG'], width=80)
        with col2:
            st.write(f"**{row['PLAYER_NAME']}**")
            # En simpel bar
            val = (row['DIST'] / df['DIST'].max()) * 100
            st.markdown(f'<div style="background:red; width:{val}%; height:10px; border-radius:5px;"></div>', unsafe_allow_html=True)
            st.caption(f"{row['DIST']/1000:.2f} km  |  {int(row['HSR'])}m HSR  |  {row['SPEED']} km/t")
