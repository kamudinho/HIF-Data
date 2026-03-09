import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent dataframes med de korrekte nøgler
    # Vi bruger 'opta_player_linebreaks' som du har navngivet den i din query
    df_lb = dp.get("opta_player_linebreaks", pd.DataFrame())
    df_local = dp.get("local_players", pd.DataFrame())

    if df_lb.empty:
        st.warning("Ingen linebreak-data fundet for de valgte filtre.")
        return

    # Sørg for at alle kolonnenavne fra SQL er store bogstaver for en sikkerheds skyld
    df_lb.columns = [c.upper() for c in df_lb.columns]
    
    # 2. Map navne via local_players (din players.csv)
    if not df_local.empty:
        df_local.columns = [c.upper() for c in df_local.columns]
        
        # Vi opretter en renset JOIN-nøgle i begge tabeller for at sikre et fejlfrit match
        df_lb['JOIN_ID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
        df_local['JOIN_ID'] = df_local['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
        
        # Tjekker om din CSV bruger 'PLAYER_NAME' eller 'NAVN'
        navn_col = 'PLAYER_NAME' if 'PLAYER_NAME' in df_local.columns else 'NAVN'
        
        # Vi laver en "Left Join" (merge) for at få navnene ind i linebreak-tabellen
        df = pd.merge(
            df_lb, 
            df_local[['JOIN_ID', navn_col]], 
            on='JOIN_ID', 
            how='left'
        )
        
        # Opret den endelige navne-kolonne (hvis spilleren ikke findes i CSV, vis UUID)
        df['SPILLER_NAVN'] = df[navn_col].fillna(df['PLAYER_OPTAUUID'])
    else:
        # Fallback hvis players.csv af en grund ikke er indlæst
        df = df_lb.copy()
        df['SPILLER_NAVN'] = df['PLAYER_OPTAUUID']

    # 3. Præsentation af tabel
    st.subheader("HIF Linebreak Analyse")
    
    # Sorter efter LB_TOTAL så de bedste står øverst
    df = df.sort_values(by='LB_TOTAL', ascending=False)
    
    # Vælg og omdøb kolonner til pæn visning
    display_df = df[['SPILLER_NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']].copy()
    display_df.columns = ['Spiller', 'Total Linebreaks', 'Angrebslinje', 'Midtbane', 'Forsvar']
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # 4. Top 10 Graf
    st.divider()
    top_10 = df.head(10).sort_values(by='LB_TOTAL', ascending=True)
    
    fig = px.bar(
        top_10, 
        x='LB_TOTAL', 
        y='SPILLER_NAVN', 
        orientation='h',
        title="Top 10 Linebreakers",
        labels={'LB_TOTAL': 'Antal', 'SPILLER_NAVN': 'Spiller'},
        color_discrete_sequence=['#df003b'] # Hvidovre Rød
    )
    
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
