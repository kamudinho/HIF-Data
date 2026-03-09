import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent data
    df_lb = dp.get("opta_player_linebreaks", dp.get("player_linebreaks", pd.DataFrame()))
    name_map = dp.get("name_map", {})

    if df_lb.empty:
        st.warning("Ingen linebreak-data fundet.")
        return

    # Sørg for at alle kolonnenavne er STORE BOGSTAVER
    df_lb.columns = [c.upper().strip() for c in df_lb.columns]
    
    # 2. Find spiller-kolonne
    possible_id_cols = ['PLAYER_OPTAUUID', 'PLAYER_ID', 'PLAYER_UUID']
    player_col = next((c for c in possible_id_cols if c in df_lb.columns), None)
    
    if not player_col:
        st.error(f"Kunne ikke finde spiller-ID. Kolonner fundet: {list(df_lb.columns)}")
        return

    # 3. Mapping Logik
    df = df_lb.copy()
    df['JOIN_ID'] = df[player_col].astype(str).str.lower().str.strip()
    df['SPILLER_NAVN'] = df['JOIN_ID'].map(name_map).fillna(df[player_col])

    # Konverter tal
    num_cols = ['LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- 4. TABS OG VISNING ---
    tab1, tab2 = st.tabs(["Oversigt", "Grafer"])

    with tab1:
        display_df = df.sort_values(by='LB_TOTAL', ascending=False)
        final_cols = ['SPILLER_NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']
        existing_final = [c for c in final_cols if c in display_df.columns]
        
        st.dataframe(
            display_df[existing_final],
            use_container_width=True,
            hide_index=True,
            height=min((len(display_df) * 35) + 38, 800)
        )

    with tab2:
        top_10 = df.sort_values(by='LB_TOTAL', ascending=True).tail(10)
        
        if not top_10.empty and 'LB_TOTAL' in top_10.columns:
            fig = px.bar(
                top_10, 
                x='LB_TOTAL', 
                y='SPILLER_NAVN', 
                orientation='h',
                title="Top 10 Linebreakers",
                # Her bruger vi discrete sequence for at få den præcise røde farve på alle søjler
                color_discrete_sequence=['#df003b'],
                text_auto='.0f'
            )
            
            fig.update_layout(
                yaxis={'categoryorder':'total ascending'}, 
                height=500,
                xaxis_title="Antal Linebreaks",
                yaxis_title="",
                # Fjerner farveskala-legenden da alle er samme farve
                showlegend=False
            )
            
            # Gør teksten på søjlerne hvid og placeret indeni for et cleaner look
            fig.update_traces(textposition='inside', textfont_color="white")
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ingen data til rådighed for grafen.")
