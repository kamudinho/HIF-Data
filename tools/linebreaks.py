import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # Hent dataframe fra data-dictionary
    df = dp.get("opta_player_linebreaks", pd.DataFrame()) # Sørg for nøglen matcher din query-nøgle
    name_map = {str(k).lower().strip(): v for k, v in dp.get("name_map", {}).items()}

    if df.empty:
        st.warning("Ingen linebreak-data fundet for de valgte filtre.")
        return

    # Sørg for ensartede kolonnenavne (UPPERCASE)
    df.columns = [c.upper() for c in df.columns]
    
    # Map navne fra players.csv - vi bruger PLAYER_OPTAUUID som nøgle
    df['NAVN'] = df['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip().map(name_map).fillna(df['PLAYER_OPTAUUID'])

    # Oversigtstabel med pæne titler
    st.subheader("Truppens Linebreak-performance")
    
    # Vi runder af og rydder op i visningen
    display_df = df[['NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']].copy()
    display_df.columns = ['Spiller', 'Total', 'Angrebslinje', 'Midtbane', 'Forsvar']
    
    st.dataframe(
        display_df.sort_values(by='Total', ascending=False),
        use_container_width=True,
        hide_index=True
    )

    # Visualisering af top-performere
    st.divider()
    
    # Sorterer data til bar chart
    plot_df = df.nlargest(10, 'LB_TOTAL').sort_values(by='LB_TOTAL', ascending=True)
    
    fig = px.bar(
        plot_df, 
        x='LB_TOTAL', 
        y='NAVN', 
        orientation='h', 
        title="Top 10 Linebreakers (Antal)",
        labels={'LB_TOTAL': 'Antal Linebreaks', 'NAVN': 'Spiller'},
        color_discrete_sequence=['#df003b'] # Hvidovre Rød
    )
    
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    
    st.plotly_chart(fig, use_container_width=True)
