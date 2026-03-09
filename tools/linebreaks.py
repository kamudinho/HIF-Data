import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent data
    # Vi tjekker begge mulige navne for dataframe-nøglen
    df_lb = dp.get("opta_player_linebreaks", dp.get("player_linebreaks", pd.DataFrame()))
    name_map = dp.get("name_map", {})

    if df_lb.empty:
        st.warning("⚠️ Ingen linebreak-data fundet i 'opta_player_linebreaks'.")
        return

    # Sørg for at alle kolonnenavne er STORE BOGSTAVER
    df_lb.columns = [c.upper().strip() for c in df_lb.columns]
    
    # 2. Find den rigtige spiller-kolonne (Opta bruger ofte forskellige navne)
    possible_id_cols = ['PLAYER_OPTAUUID', 'PLAYER_ID', 'PLAYER_UUID']
    player_col = next((c for c in possible_id_cols if c in df_lb.columns), None)
    
    if not player_col:
        st.error(f"Kunne ikke finde en spiller-ID kolonne. Tilgængelige kolonner: {list(df_lb.columns)}")
        return

    # 3. Mapping Logik (Præcis som xG-siden)
    # Vi laver en kopi for ikke at ødelægge original-data
    df = df_lb.copy()
    
    # Rens ID'erne for at matche name_map (små bogstaver, ingen mellemrum)
    df['JOIN_ID'] = df[player_col].astype(str).str.lower().str.strip()
    
    # Oversæt via name_map
    df['SPILLER_NAVN'] = df['JOIN_ID'].map(name_map).fillna(df[player_col])

    # Sørg for at numeriske kolonner rent faktisk er tal (vigtigt for sortering og grafer)
    num_cols = ['LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- 4. TABS OG VISNING ---
    tab1, tab2 = st.tabs(["Oversigt", "Grafer"])

    with tab1:
        # Sorter efter Total
        display_df = df.sort_values(by='LB_TOTAL', ascending=False)
        
        # Vælg kolonner til tabel
        final_cols = ['SPILLER_NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']
        # Vi viser kun de kolonner der rent faktisk findes i din SQL-data
        existing_final = [c for c in final_cols if c in display_df.columns]
        
        st.dataframe(
            display_df[existing_final],
            use_container_width=True,
            hide_index=True,
            height=min((len(display_df) * 35) + 38, 800)
        )

    with tab2:
        # Top 10 Graf
        top_10 = df.sort_values(by='LB_TOTAL', ascending=True).tail(10)
        
        if not top_10.empty and 'LB_TOTAL' in top_10.columns:
            fig = px.bar(
                top_10, 
                x='LB_TOTAL', 
                y='SPILLER_NAVN', 
                orientation='h',
                title="Top 10 Linebreakers",
                color='LB_TOTAL', 
                color_continuous_scale='#df003b',
                text_auto=True
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ingen data til rådighed for grafen.")
