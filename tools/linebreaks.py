import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    df_lb = dp.get("opta_player_linebreaks", pd.DataFrame())
    df_local = dp.get("local_players", pd.DataFrame())

    if df_lb.empty:
        st.warning("Ingen linebreak-data fundet.")
        return

    df_lb.columns = [c.upper() for c in df_lb.columns]
    
    # mapping logik
    if not df_local.empty:
        df_local.columns = [c.upper().strip() for c in df_local.columns]
        
        # VIGTIGT: Vi tvinger begge til string og fjerner alt whitespace
        df_lb['JOIN_ID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
        df_local['JOIN_ID'] = df_local['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
        
        navn_col = 'NAVN' if 'NAVN' in df_local.columns else 'PLAYER_NAME'
        
        df = pd.merge(df_lb, df_local[['JOIN_ID', navn_col]], on='JOIN_ID', how='left')
        df['SPILLER_NAVN'] = df[navn_col].fillna(df['PLAYER_OPTAUUID'])
        
        # DEBUG SEKTION (Viser kun hvis noget er galt)
        missing_count = df[navn_col].isna().sum()
        if missing_count > 0:
            with st.expander(f"⚠️ Debug: {missing_count} spillere mangler navn"):
                st.write("Disse ID'er fra Snowflake findes IKKE i din CSV:")
                st.write(df[df[navn_col].isna()]['PLAYER_OPTAUUID'].unique())
    else:
        df = df_lb.copy()
        df['SPILLER_NAVN'] = df['PLAYER_OPTAUUID']

    # --- TABS ---
    tab1, tab2 = st.tabs(["📋 Oversigt", "📊 Grafer"])

    with tab1:
        st.subheader("HIF Linebreak Analyse")
        display_df = df.sort_values(by='LB_TOTAL', ascending=False).copy()
        cols = ['SPILLER_NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']
        existing = [c for c in cols if c in display_df.columns]
        table_final = display_df[existing]
        table_final.columns = ['Spiller', 'Total', 'Angreb', 'Midtbane', 'Forsvar'][:len(existing)]
        
        st.dataframe(table_final, use_container_width=True, hide_index=True)

    with tab2:
        top_10 = df.sort_values(by='LB_TOTAL', ascending=True).tail(10)
        fig = px.bar(top_10, x='LB_TOTAL', y='SPILLER_NAVN', orientation='h',
                     title="Top 10 Linebreakers",
                     color='LB_TOTAL', color_continuous_scale='Reds', text='LB_TOTAL')
        st.plotly_chart(fig, use_container_width=True)
