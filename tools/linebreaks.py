import streamlit as st
import pandas as pd

def vis_side(dp):
    df = dp.get("player_linebreaks", pd.DataFrame())
    name_map = {str(k).lower().strip(): v for k, v in dp.get("name_map", {}).items()}

    if df.empty:
        st.warning("Ingen data fundet for de valgte filtre.")
        return

    df.columns = [c.upper() for c in df.columns]
    
    # Map navne fra players.csv
    df['NAVN'] = df['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip().map(name_map).fillna(df['PLAYER_OPTAUUID'])

    # Oversigtstabel
    st.subheader("Truppens Linebreak-performance")
    st.dataframe(
        df[['NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']],
        use_container_width=True,
        hide_index=True
    )

    # Plot
    fig = px.bar(df.head(10), x='LB_TOTAL', y='NAVN', orientation='h', 
                 title="Top 10 Linebreakers", color_discrete_sequence=['#df003b'])
    st.plotly_chart(fig, use_container_width=True)
