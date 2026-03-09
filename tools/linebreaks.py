import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent dataframes
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_players = dp.get("local_players", pd.DataFrame())

    if df_lb.empty:
        st.warning("Ingen linebreak-data fundet.")
        return

    # 2. Forbered linebreak-data (Sørg for UPPERCASE kolonner)
    df_lb.columns = [c.upper() for c in df_lb.columns]
    
    # 3. Forbered spiller-data fra players.csv
    if not df_players.empty:
        df_players.columns = [c.upper() for c in df_players.columns]
        
        # Identificer navne-kolonnen (typisk 'PLAYER_NAME' eller 'NAVN')
        navn_col = 'PLAYER_NAME' if 'PLAYER_NAME' in df_players.columns else 'NAVN'
        
        # Rens UUID'er for at sikre match (fjerner whitespaces og gør små bogstaver)
        df_lb['JOIN_ID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
        df_players['JOIN_ID'] = df_players['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()

        # Lav merge (vi tager kun de kolonner vi skal bruge fra players.csv)
        df_merged = pd.merge(
            df_lb, 
            df_players[['JOIN_ID', navn_col]], 
            on='JOIN_ID', 
            how='left'
        )
        
        # Lav den endelige navne-kolonne
        df_merged['SPILLER'] = df_merged[navn_col].fillna(df_merged['PLAYER_OPTAUUID'])
    else:
        df_merged = df_lb.copy()
        df_merged['SPILLER'] = df_merged['PLAYER_OPTAUUID']

    # 4. Visning af tabel
    st.subheader("Truppens Linebreak-performance")
    
    # Sorter efter flest linebreaks
    df_merged = df_merged.sort_values(by='LB_TOTAL', ascending=False)
    
    display_df = df_merged[['SPILLER', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']].copy()
    display_df.columns = ['Spiller', 'Total', 'Angrebslinje', 'Midtbane', 'Forsvar']
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # 5. Visualisering
    st.divider()
    top_10 = df_merged.nlargest(10, 'LB_TOTAL').sort_values(by='LB_TOTAL', ascending=True)
    
    fig = px.bar(
        top_10, 
        x='LB_TOTAL', 
        y='SPILLER', 
        orientation='h',
        title="Top 10 Linebreakers",
        color_discrete_sequence=['#df003b'],
        labels={'LB_TOTAL': 'Antal Linebreaks', 'SPILLER': 'Spiller'}
    )
    st.plotly_chart(fig, use_container_width=True)
