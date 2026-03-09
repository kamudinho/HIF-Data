import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent dataframes og name_map (ligesom på xG-siden)
    df_lb = dp.get("opta_player_linebreaks", pd.DataFrame())
    name_map = dp.get("name_map", {}) # Vi bruger den eksisterende name_map

    if df_lb.empty:
        st.warning("⚠️ Ingen linebreak-data fundet.")
        return

    # Sørg for store bogstaver i kolonnenavne fra Snowflake
    df_lb.columns = [c.upper() for c in df_lb.columns]
    
    # 2. Mapping Logik (Samme metode som xG-siden)
    # Vi renser ID'et så det er identisk med nøglerne i dit name_map
    df_lb['JOIN_ID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
    
    # Oversæt ID til Navn via name_map. Hvis ikke fundet, behold UUID
    df_lb['SPILLER_NAVN'] = df_lb['JOIN_ID'].map(name_map).fillna(df_lb['PLAYER_OPTAUUID'])

    # 3. Opsætning af Tabs
    st.subheader("HIF Linebreak Analyse")
    tab1, tab2 = st.tabs(["📋 Oversigt", "📊 Grafer"])

    with tab1:
        # Klargør tabel til visning
        display_df = df_lb.sort_values(by='LB_TOTAL', ascending=False).copy()
        
        # Vælg relevante kolonner
        cols_to_show = ['SPILLER_NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']
        existing_cols = [c for c in cols_to_show if c in display_df.columns]
        
        table_final = display_df[existing_cols]
        table_final.columns = ['Spiller', 'Total', 'Angreb', 'Midtbane', 'Forsvar'][:len(existing_cols)]
        
        # Dynamisk højde baseret på antal spillere
        calc_height = min((len(table_final) * 35) + 38, 800)
        
        st.dataframe(
            table_final,
            use_container_width=True,
            hide_index=True,
            height=calc_height
        )

    with tab2:
        # Top 10 Graf
        top_10 = df_lb.sort_values(by='LB_TOTAL', ascending=True).tail(10)
        
        fig = px.bar(
            top_10, 
            x='LB_TOTAL', 
            y='SPILLER_NAVN', 
            orientation='h',
            title="Top 10 Linebreakers",
            labels={'LB_TOTAL': 'Antal Linebreaks', 'SPILLER_NAVN': 'Spiller'},
            color='LB_TOTAL', 
            color_continuous_scale='Reds', 
            text='LB_TOTAL'
        )
        
        fig.update_layout(
            yaxis={'categoryorder':'total ascending'},
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # Hurtig oversigt over linje-typer for top 5
        st.write("---")
        st.caption("Detaljeret fordeling (Top 5)")
        top_5 = df_lb.sort_values(by='LB_TOTAL', ascending=False).head(5)
        fig_lines = px.bar(
            top_5,
            x='SPILLER_NAVN',
            y=['LB_DEFENCE_LINE', 'LB_MIDFIELD_LINE', 'LB_ATTACK_LINE'],
            barmode='group',
            color_discrete_sequence=['#ffcccc', '#ff6666', '#df003b'],
            labels={'value': 'Antal', 'variable': 'Linje'}
        )
        st.plotly_chart(fig_lines, use_container_width=True)
