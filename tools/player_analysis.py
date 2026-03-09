import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. HENT DATA
    df_lb_raw = dp.get("player_linebreaks", pd.DataFrame())
    df_xg = dp.get("opta_expected_goals", pd.DataFrame()) # Eller din xG nøgle
    name_map = dp.get("name_map", {})

    if df_lb_raw.empty and df_xg.empty:
        st.error("Ingen data fundet i systemet.")
        return

    # 2. STANDARDISER KOLONNER TIL STORE BOGSTAVER (Vigtigt for Opta-dump)
    if not df_lb_raw.empty:
        df_lb_raw.columns = [c.upper() for c in df_lb_raw.columns]
    if not df_xg.empty:
        df_xg.columns = [c.upper() for c in df_xg.columns]

    # 3. SPILLERVALG (Baseret på alle tilgængelige spillere)
    all_uuids = set()
    if not df_lb_raw.empty: all_uuids.update(df_lb_raw['PLAYER_OPTAUUID'].unique())
    if not df_xg.empty: all_uuids.update(df_xg['PLAYER_OPTAUUID'].unique())
    
    spiller_liste = {name_map.get(uuid, uuid): uuid for uuid in all_uuids}
    valgt_navn = st.selectbox("Vælg spiller", options=sorted(spiller_liste.keys()))
    valgt_uuid = spiller_liste[valgt_navn]

    st.title(f"Analyse: {valgt_navn}")

    # --- SEKTION 1: EXPECTED GOALS (Din oprindelige logik) ---
    st.subheader("Afslutninger & xG")
    p_xg = df_xg[df_xg['PLAYER_OPTAUUID'] == valgt_uuid] if not df_xg.empty else pd.DataFrame()
    
    if not p_xg.empty:
        # Her kan du indsætte din eksisterende xG-graf/metrics
        total_xg = p_xg[p_xg['STAT_TYPE'] == 'expectedGoals']['STAT_VALUE'].sum()
        st.metric("Total xG", round(total_xg, 2))
    else:
        st.info("Ingen xG-data for denne spiller.")

    # --- SEKTION 2: LINEBREAKS (Den nye transformation) ---
    st.divider()
    st.subheader("Linebreaks & Progression")
    
    p_lb = df_lb_raw[df_lb_raw['PLAYER_OPTAUUID'] == valgt_uuid].copy()
    
    if not p_lb.empty:
        # Vi laver 'Long' format om til 'Wide', så vi kan lave grafer
        # Dette sikrer at 'total', 'oneLine' osv bliver til brugbare tal
        lb_clean = p_lb[~p_lb['STAT_TYPE'].str.contains('percentage', case=False)]
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Bar chart over antal linebreaks per type
            fig_lb = px.bar(lb_clean, 
                          x='STAT_TYPE', 
                          y='STAT_VALUE',
                          title="Linebreak Typer",
                          labels={'STAT_VALUE': 'Antal', 'STAT_TYPE': 'Type'},
                          color_discrete_sequence=['#FF4B4B'])
            st.plotly_chart(fig_lb, use_container_width=True)
            
        with col2:
            # Vis den rå tabel for dem der elsker tal (fx Smeds stats)
            st.write("Detaljerede tal")
            st.dataframe(p_lb[['STAT_TYPE', 'STAT_VALUE', 'STAT_FH', 'STAT_SH']], 
                         hide_index=True, use_container_width=True)
    else:
        st.info("Ingen Linebreak-data for denne spiller.")
