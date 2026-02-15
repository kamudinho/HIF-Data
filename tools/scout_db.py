import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 1. HJÆLPEFUNKTIONER ---
def rens_metrik_vaerdi(val):
    """Sikrer at vi altid har et heltal til metrikker."""
    try:
        if pd.isna(val): return 0
        return int(float(val))
    except:
        return 0

def vis_metrikker(row):
    """Viser de 8 kerne-metrikker i et grid."""
    m_cols = st.columns(4)
    metrics = [
        ("Beslutsomhed", "Beslutsomhed"), ("Fart", "Fart"), 
        ("Aggresivitet", "Aggresivitet"), ("Attitude", "Attitude"),
        ("Udholdenhed", "Udholdenhed"), ("Lederegenskaber", "Lederegenskaber"), 
        ("Teknik", "Teknik"), ("Spilintelligens", "Spilintelligens")
    ]
    for i, (label, col) in enumerate(metrics):
        val = rens_metrik_vaerdi(row.get(col, 0))
        m_cols[i % 4].metric(label, f"{val}")

# --- 2. PROFIL DIALOG (POP-UP) ---
@st.dialog(" ", width="large")
def vis_profil(p_data, full_df, s_df, hif_avg):
    st.subheader(f"{p_data['NAVN']} | {p_data['POSITION']} | {p_data['KLUB']}")
    st.divider()

    historik = full_df[full_df['ID'] == p_data['ID']].sort_values('DATO', ascending=True)
    
    # Tabs uden ikoner som ønsket
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Grafik"])
    
    with tab1:
        nyeste = historik.iloc[-1]
        vis_metrikker(nyeste)
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', 'Ingen data')}")
        with c2: st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', 'Ingen data')}")
        with c3: st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', 'Ingen data')}")

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            with st.expander(f"Rapport fra {row['DATO']} (Rating: {row['RATING_AVG']})"):
                vis_metrikker(row)

    with tab3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=historik['DATO'], y=historik['RATING_AVG'], mode='lines+markers', name="Rating"))
        fig.update_layout(height=300, yaxis=dict(range=[1, 7]), margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        if s_df.empty:
            st.info("Ingen kampdata fundet.")
        else:
            sp_stats = s_df[s_df['PLAYER_WYID'].astype(str) == str(p_data['ID'])].copy()
            st.dataframe(sp_stats[["SEASONNAME", "TEAMNAME", "APPEARANCES", "GOAL"]], use_container_width=True, hide_index=True)

    with tab5:
        # Radardiagram over færdigheder
        nyeste = historik.iloc[-1]
        m_navne = ["Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"]
        m_værdier = [rens_metrik_vaerdi(nyeste.get(m.upper(), nyeste.get(m, 0))) for m in m_navne]
        
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=m_værdier,
            theta=m_navne,
            fill='toself',
            line_color='#cc0000'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
            showlegend=False,
            height=400
        )
        st.plotly_chart(fig_radar, use_container_width=True)

# --- 3. HOVEDFUNKTION TIL SIDEN ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet. Genindlæs siden.")
        return
    
    # Udpak data fra HIF-dash.py
    # ev, _, h_map, spillere, stats_df, df_scout
    _, _, _, _, stats_df, df = st.session_state["main_data"]

    st.markdown("<p style='font-size: 14px; font-weight: bold; margin-bottom: 20px;'>Scouting Database</p>", unsafe_allow_html=True)

    # --- FILTRERING ---
    c1, c2 = st.columns([3, 1])
    with c1:
        search = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
    with c2:
        with st.popover("Filtre"):
            f_pos = st.multiselect("Positioner", options=sorted(df['POSITION'].unique().tolist()))
            f_rating = st.slider("Rating (Snit)", 1.0, 7.0, (1.0, 7.0), step=0.1)

    # --- DATA BEHANDLING ---
    # Find nyeste rapport pr. spiller
    rapport_counts = df.groupby('ID').size().reset_index(name='RAPPORTER')
    latest_reports = df.sort_values('DATO').groupby('ID').tail(1)
    final_df = pd.merge(latest_reports, rapport_counts, on='ID')
    
    # Anvend filtre
    if search:
        final_df = final_df[final_df['NAVN'].str.contains(search, case=False) | final_df['KLUB'].str.contains(search, case=False)]
    if f_pos:
        final_df = final_df[final_df['POSITION'].isin(f_pos)]
    
    final_df = final_df[(final_df['RATING_AVG'] >= f_rating[0]) & (final_df['RATING_AVG'] <= f_rating[1])]

    # Beregn HIF gennemsnit til reference
    hif_avg = df[df['KLUB'].str.contains('Hvidovre', case=False, na=False)]['RATING_AVG'].mean()

    # --- TABEL ---
    tabel_hoejde = (len(final_df) * 35) + 45
    event = st.dataframe(
        final_df[["NAVN", "POSITION", "KLUB", "RATING_AVG", "STATUS", "RAPPORTER", "DATO"]],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        height=min(tabel_hoejde, 600),
        column_config={
            "RATING_AVG": st.column_config.NumberColumn("Snit", format="%.1f"),
            "DATO": st.column_config.DateColumn("Seneste")
        }
    )

    # --- ÅBN PROFIL VED VALG ---
    if len(event.selection.rows) > 0:
        vis_profil(final_df.iloc[event.selection.rows[0]], df, stats_df, hif_avg)
