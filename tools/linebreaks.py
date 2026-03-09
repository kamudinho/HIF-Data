import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. RENT LINEBREAK DATA-FETCH ---
    df_lb = dp.get("opta_player_linebreaks", pd.DataFrame())
    name_map = dp.get("name_map", {})

    # Tving kolonner til STORE bogstaver (Snowflake standard)
    if not df_lb.empty:
        df_lb.columns = [c.upper() for c in df_lb.columns]

    # Stop hvis tabellen er tom
    if df_lb.empty:
        st.warning("⚠️ Ingen Linebreak-data fundet i 'opta_player_linebreaks'.")
        return

    # --- 2. DATABEHANDLING ---
    # Vi bruger PLAYER_OPTAUUID som unik nøgle
    df_lb['PLAYER_OPTAUUID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
    
    # Lav en opsummering pr. spiller (kun volumental, ikke procenter)
    volumen_df = df_lb[~df_lb['STAT_TYPE'].str.contains('percentage', case=False)].copy()
    
    # Vi finder den samlede 'total' stat for hver spiller for at kunne sortere
    totals = volumen_df[volumen_df['STAT_TYPE'] == 'total'].groupby('PLAYER_OPTAUUID')['STAT_VALUE'].sum().reset_index()
    totals['NAVN'] = totals['PLAYER_OPTAUUID'].map(name_map).fillna(totals['PLAYER_OPTAUUID'])
    totals = totals.sort_values('STAT_VALUE', ascending=False)

    # --- 3. UI LAYOUT ---
    st.title("Linebreak Analyse")

    # Spiller-vælger (baseret på hvem der rent faktisk har LB-data)
    all_names = totals['NAVN'].tolist()
    selected_navn = st.selectbox("Vælg spiller", options=all_names)
    selected_uuid = totals[totals['NAVN'] == selected_navn]['PLAYER_OPTAUUID'].iloc[0]

    # To kolonner: Liste og Detaljer
    col_list, col_chart = st.columns([1, 2])

    with col_list:
        st.subheader("Rangliste (Total)")
        st.dataframe(
            totals[['NAVN', 'STAT_VALUE']].rename(columns={'STAT_VALUE': 'Antal'}),
            use_container_width=True,
            hide_index=True,
            height=400
        )

    with col_chart:
        st.subheader(f"Profil: {selected_navn}")
        
        # Data for den valgte spiller
        p_data = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_uuid].copy()
        
        # Graf over forskellige typer linebreaks (fjern 'total' og procenter for at se fordelingen)
        plot_df = p_data[
            (~p_data['STAT_TYPE'].str.contains('percentage', case=False)) & 
            (p_data['STAT_TYPE'] != 'total')
        ].sort_values('STAT_VALUE', ascending=True)

        fig = px.bar(
            plot_df, 
            x='STAT_VALUE', 
            y='STAT_TYPE', 
            orientation='h',
            color_discrete_sequence=['#df003b'],
            labels={'STAT_VALUE': 'Antal', 'STAT_TYPE': ''}
        )
        fig.update_layout(margin=dict(l=10, r=10, t=0, b=0), height=350)
        st.plotly_chart(fig, use_container_width=True)

    # --- 4. HALVLEGS-STATISTIK ---
    st.write("---")
    st.subheader("Detaljeret oversigt (inkl. FH/SH)")
    st.dataframe(
        p_data[['STAT_TYPE', 'STAT_VALUE', 'STAT_FH', 'STAT_SH']].sort_values('STAT_VALUE', ascending=False),
        use_container_width=True,
        hide_index=True
    )
