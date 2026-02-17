import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def vis_side(df_team_matches, hold_map):
    st.title("Modstanderanalyse")
    
    if df_team_matches is None or df_team_matches.empty:
        st.error("Ingen kampdata fundet i Snowflake.")
        return

    # 1. Valg af hold
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    valgt_id = navne_dict[valgt_navn]

    # 2. Filtrering og sortering
    df_filtreret = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_filtreret['DATE'] = pd.to_datetime(df_filtreret['DATE'])
    df_filtreret = df_filtreret.sort_values('DATE', ascending=True)

    # 3. Metrics øverst
    col1, col2, col3, col4 = st.columns(4)
    seneste_xg = df_filtreret['XG'].iloc[-1] if not df_filtreret.empty else 0
    col1.metric("Kampe analyseret", len(df_filtreret))
    col2.metric("Gns. xG", round(df_filtreret['XG'].mean(), 2))
    col3.metric("Seneste xG", round(seneste_xg, 2))
    col4.metric("Gns. Possession", f"{round(df_filtreret['POSSESSIONPERCENT'].mean(), 1)}%")

    st.markdown("---")

    # --- BANE 1: xG TREND (FORM) ---
    st.subheader("xG pr. kamp")
    fig_xg = px.line(df_filtreret, x='DATE', y='XG', title=f"xG udvikling for {valgt_navn}",
                     labels={'XG': 'Expected Goals', 'DATE': 'Dato'},
                     line_shape='spline', render_mode='svg')
    fig_xg.add_hline(y=df_filtreret['XG'].mean(), line_dash="dot", line_color="red", annotation_text="Gennemsnit")
    fig_xg.update_traces(line_color='#003366')
    st.plotly_chart(fig_xg, use_container_width=True)

    # --- BANE 3: DEFENSIVT PRES (PPDA) ---
    st.subheader("🛡️ Defensiv Struktur (PPDA - Jo lavere, jo højere pres)")
    # PPDA forklares: Lav PPDA = Aggressivt pres. Høj PPDA = Afventende.
    fig_ppda = px.area(df_filtreret, x='DATE', y='PPDA', 
                       title="PPDA Trend (Pres-intensitet)",
                       labels={'PPDA': 'Passes Per Defensive Action'},
                       color_discrete_sequence=['#2ecc71'])
    st.plotly_chart(fig_ppda, use_container_width=True)

    # 4. Rå data tabel nederst
    with st.expander("Se alle rå kampdata"):
        st.dataframe(df_filtreret.sort_values('DATE', ascending=False), use_container_width=True)
