import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- 1. HJÆLPEFUNKTIONER ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        return float(val)
    except:
        return 0.0

def vis_metrikker(row):
    m_cols = st.columns(4)
    metrics = [
        ("Beslutsomhed", "Beslutsomhed"), ("Fart", "Fart"), 
        ("Aggresivitet", "Aggresivitet"), ("Attitude", "Attitude"),
        ("Udholdenhed", "Udholdenhed"), ("Lederegenskaber", "Lederegenskaber"), 
        ("Teknik", "Teknik"), ("Spilintelligens", "Spilintelligens")
    ]
    for i, (label, col) in enumerate(metrics):
        val = rens_metrik_vaerdi(row.get(col, 0))
        m_cols[i % 4].metric(label, f"{int(val)}")

# --- 2. PROFIL DIALOG ---
@st.dialog(" ", width="large")
def vis_profil(p_data, full_df, s_df):
    # Overskrift bygget i Streamlit i stedet for Plotly for at undgå fejl
    st.markdown(f"""
        <div style='text-align: center;'>
            <h2 style='margin-bottom: 0;'>{p_data['NAVN']}</h2>
            <p style='font-size: 18px; color: gray;'>{p_data['KLUB']} | {p_data['POSITION']} | Snit: {p_data['RATING_AVG']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    historik = full_df[full_df['ID'] == p_data['ID']].sort_values('DATO', ascending=True)
    nyeste = historik.iloc[-1]
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Grafik Card"])
    
    with tab1:
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
        fig.add_trace(go.Scatter(x=historik['DATO'], y=historik['RATING_AVG'], mode='lines+markers', line_color='#cc0000'))
        fig.update_layout(height=300, yaxis=dict(range=[1, 7]), margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        if s_df.empty: st.info("Ingen kampdata fundet.")
        else:
            sp_stats = s_df[s_df['PLAYER_WYID'].astype(str) == str(p_data['ID'])].copy()
            st.dataframe(sp_stats[["SEASONNAME", "TEAMNAME", "APPEARANCES", "GOAL"]], use_container_width=True, hide_index=True)

    with tab5:
        # DATA TIL RADAR
        m_navne = ["Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"]
        m_værdier = [rens_metrik_vaerdi(nyeste.get(m.upper(), nyeste.get(m, 0))) for m in m_navne]
        # Luk cirklen
        m_værdier.append(m_værdier[0])
        m_theta = m_navne + [m_navne[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=m_værdier,
            theta=m_theta,
            fill='toself',
            fillcolor='rgba(204, 0, 0, 0.2)',
            line=dict(color='#cc0000', width=2)
        ))

        # Meget simpelt layout uden titler eller komplekse dicts
        fig_radar.update_layout(
            polar=dict(
                gridshape='polygon',
                radialaxis=dict(visible=True, range=[0, 7])
            ),
            showlegend=False,
            height=500,
            margin=dict(t=30, b=30, l=30, r=30)
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
        st.markdown(f"<div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px;'><b>Vurdering:</b><br>{nyeste.get('VURDERING', 'N/A')}</div>", unsafe_allow_html=True)

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    _, _, _, _, stats_df, df = st.session_state["main_data"]

    # Top bar
    st.markdown("<p style='font-size: 14px; font-weight: bold; margin-bottom: 20px;'>Scouting Database</p>", unsafe_allow_html=True)

    # Filtrering
    c1, c2 = st.columns([3, 1])
    with c1:
        search = st.text_input("Søg", placeholder="Navn eller klub...", label_visibility="collapsed")
    with c2:
        with st.popover("Filtre"):
            f_pos = st.multiselect("Positioner", options=sorted(df['POSITION'].unique().tolist()))
            f_rating = st.slider("Rating", 1.0, 7.0, (1.0, 7.0), step=0.1)

    # Data behandling
    rapport_counts = df.groupby('ID').size().reset_index(name='RAPPORTER')
    latest_reports = df.sort_values('DATO').groupby('ID').tail(1)
    f_df = pd.merge(latest_reports, rapport_counts, on='ID')
    
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False) | f_df['KLUB'].str.contains(search, case=False)]
    if f_pos:
        f_df = f_df[f_df['POSITION'].isin(f_pos)]
    f_df = f_df[(f_df['RATING_AVG'] >= f_rating[0]) & (f_df['RATING_AVG'] <= f_rating[1])]
    
    # --- PAGINERING ---
    items_per_page = 20
    total_pages = max(1, int(np.ceil(len(f_df) / items_per_page)))
    
    if 'scout_page' not in st.session_state: st.session_state.scout_page = 1
    if st.session_state.scout_page > total_pages: st.session_state.scout_page = total_pages

    start_idx = (st.session_state.scout_page - 1) * items_per_page
    page_df = f_df.iloc[start_idx : start_idx + items_per_page]

    # Tabelvisning
    tabel_hoejde = (len(page_df) * 35) + 40
    event = st.dataframe(
        page_df[["NAVN", "POSITION", "KLUB", "RATING_AVG", "STATUS", "RAPPORTER", "DATO"]],
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
        height=tabel_hoejde,
        column_config={
            "RATING_AVG": st.column_config.NumberColumn("Snit", format="%.1f"),
            "DATO": st.column_config.DateColumn("Seneste")
        }
    )

    # DISKRETE KNAPPER I BUNDEN
    if total_pages > 1:
        st.write("")
        c_prev, c_text, c_next = st.columns([1, 2, 1])
        with c_prev:
            if st.button("← Forrige", disabled=(st.session_state.scout_page <= 1), use_container_width=True):
                st.session_state.scout_page -= 1
                st.rerun()
        with c_text:
            st.markdown(f"<p style='text-align: center; margin-top: 5px;'>Side {st.session_state.scout_page} af {total_pages}</p>", unsafe_allow_html=True)
        with c_next:
            if st.button("Næste →", disabled=(st.session_state.scout_page >= total_pages), use_container_width=True):
                st.session_state.scout_page += 1
                st.rerun()

    if len(event.selection.rows) > 0:
        vis_profil(page_df.iloc[event.selection.rows[0]], df, stats_df)
