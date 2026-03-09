import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent dataframes
    df_lb = dp.get("opta_player_linebreaks", pd.DataFrame())
    df_local = dp.get("local_players", pd.DataFrame())

    if df_lb.empty:
        st.warning("Ingen linebreak-data fundet for de valgte filtre.")
        return

    # Sørg for store bogstaver i kolonnenavne fra SQL
    df_lb.columns = [c.upper() for c in df_lb.columns]
    
    # 2. Mapping Logik
    if not df_local.empty:
        # Rens kolonnenavne i din CSV (fjerner evt. usynlige mellemrum)
        df_local.columns = [c.upper().strip() for c in df_local.columns]
        
        # Opretter JOIN_ID (vigtigt for fejlfrit match)
        df_lb['JOIN_ID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
        df_local['JOIN_ID'] = df_local['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
        
        # Vi prioriterer 'NAVN' kolonnen fra din rettede CSV
        navn_col = 'NAVN' if 'NAVN' in df_local.columns else 'PLAYER_NAME'
        
        # Merge data
        df = pd.merge(
            df_lb, 
            df_local[['JOIN_ID', navn_col]], 
            on='JOIN_ID', 
            how='left'
        )
        
        # Hvis navnet mangler i CSV, brug UUID som fallback
        df['SPILLER_NAVN'] = df[navn_col].fillna(df['PLAYER_OPTAUUID'])
        
        # Lille status-tjek (kan slettes når det virker)
        fundne_navne = df[navn_col].notna().sum()
        if fundne_navne == 0:
            st.error("⚠️ Ingen match fundet mellem Data og CSV. Tjek om UUID'erne i Snowflake matcher din fil.")
    else:
        df = df_lb.copy()
        df['SPILLER_NAVN'] = df['PLAYER_OPTAUUID']
        st.info("Info: local_players (players.csv) ikke fundet.")

    # 3. Opsætning af Tabs
    st.subheader("HIF Linebreak Analyse")
    tab1, tab2 = st.tabs(["📋 Oversigt", "📊 Grafer"])

    with tab1:
        # Sorter og klargør tabel
        display_df = df.sort_values(by='LB_TOTAL', ascending=False).copy()
        
        # Vælg og omdøb kolonner til visning
        cols_to_show = ['SPILLER_NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']
        # Vi sikrer os at kolonnerne findes før vi viser dem
        existing_cols = [c for c in cols_to_show if c in display_df.columns]
        
        table_final = display_df[existing_cols].copy()
        table_final.columns = ['Spiller', 'Total', 'Angreb', 'Midtbane', 'Forsvar'][:len(existing_cols)]
        
        st.dataframe(
            table_final,
            use_container_width=True,
            hide_index=True
        )

    with tab2:
        # Top 10 Graf
        top_10 = df.sort_values(by='LB_TOTAL', ascending=False).head(10)
        # Sorter omvendt til vandret bar-chart for at få den bedste øverst
        top_10 = top_10.sort_values(by='LB_TOTAL', ascending=True)
        
        fig = px.bar(
            top_10, 
            x='LB_TOTAL', 
            y='SPILLER_NAVN', 
            orientation='h',
            title="Top 10 Linebreakers",
            labels={'LB_TOTAL': 'Antal Linebreaks', 'SPILLER_NAVN': 'Spiller'},
            color='LB_TOTAL',
            color_continuous_scale='Reds', # Flot gradient i Hvidovre-farver
            text='LB_TOTAL'
        )
        
        fig.update_layout(
            yaxis={'categoryorder':'total ascending'},
            showlegend=False,
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # Ekstra graf: Fordeling af linjer
        st.write("---")
        st.caption("Fordeling af linebreaks per kæde (Top 5)")
        top_5 = df.sort_values(by='LB_TOTAL', ascending=False).head(5)
        
        fig_lines = px.bar(
            top_5,
            x='SPILLER_NAVN',
            y=['LB_DEFENCE_LINE', 'LB_MIDFIELD_LINE', 'LB_ATTACK_LINE'],
            title="Hvor brydes linjerne?",
            labels={'value': 'Antal', 'SPILLER_NAVN': 'Spiller', 'variable': 'Linje'},
            barmode='group'
        )
        st.plotly_chart(fig_lines, use_container_width=True)
