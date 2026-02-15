import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import numpy as np

# --- 1. HJÆLPEFUNKTIONER ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or val == "": return 0
        return int(float(val))
    except:
        return 0

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
        m_cols[i % 4].metric(label, f"{val}")

# --- 2. PROFIL DIALOG ---
@st.dialog(" ", width="large")
def vis_profil(p_data, full_df, s_df):
    st.markdown(f"<div style='text-align: center;'><h2 style='margin-bottom:0;'>{p_data['NAVN']}</h2>"
                f"<p style='color: gray; font-size:16px;'>{p_data['KLUB']} | {p_data['POSITION']} | Snit: {p_data['RATING_AVG']}</p></div>", unsafe_allow_html=True)
    
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
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO'], y=historik['RATING_AVG'], mode='lines+markers', line_color='#cc0000'))
        fig_line.update_layout(height=300, yaxis=dict(range=[1, 7]), margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        if s_df.empty: st.info("Ingen kampdata fundet.")
        else:
            sp_stats = s_df[s_df['PLAYER_WYID'].astype(str) == str(p_data['ID'])].copy()
            st.dataframe(sp_stats[["SEASONNAME", "TEAMNAME", "APPEARANCES", "GOAL"]], use_container_width=True, hide_index=True)

    with tab5:
        # --- RADAR LOGIK FRA SAMMENLIGNINGSSIDEN ---
        categories = ['Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 'Udholdenhed', 'Lederevner', 'Teknik', 'Spil-int.']
        
        # Hent værdier og luk cirklen (v[0])
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']]
        v.append(v[0])
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=v, 
            theta=categories + [categories[0]], 
            fill='toself', 
            line_color='#df003b',
            name=p_data['NAVN']
        ))
        
        fig_radar.update_layout(
            polar=dict(
                gridshape='linear', # Lineær giver den kantede form
                radialaxis=dict(visible=True, range=[0, 7])
            ),
            showlegend=False, 
            height=450, 
            margin=dict(l=50, r=50, t=20, b=20)
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
        
        st.markdown(f"""
            <div style='text-align: center; background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #ddd;'>
                <p style='margin:0; font-weight:bold;'>Vurdering:</p>
                <p style='margin:0;'>{nyeste.get('VURDERING', 'N/A')}</p>
            </div>
        """, unsafe_allow_html=True)

# --- 3. HOVEDFUNKTION TIL SIDEN ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    _, _, _, _, stats_df, df = st.session_state["main_data"]

    st.markdown("<p style='font-size: 14px; font-weight: bold; margin-bottom: 20px;'>Scouting Database</p>", unsafe_allow_html=True)

    # Filtrering
    c1, c2 = st.columns([3, 1])
    with c1:
        search = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
    with c2:
        with st.popover("Filtre"):
            f_pos = st.multiselect("Positioner", options=sorted(df['POSITION'].unique().tolist()) if 'POSITION' in df.columns else [])
            f_rating = st.slider("Rating", 1.0, 7.0, (1.0, 7.0), step=0.1)

    # Data behandling
    if df.empty:
        st.info("Databasen er tom.")
        return

    latest_reports = df.sort_values('DATO').groupby('ID').tail(1)
    
    if search:
        latest_reports = latest_reports[latest_reports['NAVN'].str.contains(search, case=False) | latest_reports['KLUB'].str.contains(search, case=False)]
    if f_pos:
        latest_reports = latest_reports[latest_reports['POSITION'].isin(f_pos)]
    
    latest_reports = latest_reports[(latest_reports['RATING_AVG'] >= f_rating[0]) & (latest_reports['RATING_AVG'] <= f_rating[1])]

    # --- PAGINERING ---
    items_per_page = 20
    total_pages = max(1, int(np.ceil(len(latest_reports) / items_per_page)))
    
    if 'scout_page' not in st.session_state: st.session_state.scout_page = 1
    if st.session_state.scout_page > total_pages: st.session_state.scout_page = total_pages

    start_idx = (st.session_state.scout_page - 1) * items_per_page
    page_df = latest_reports.iloc[start_idx : start_idx + items_per_page]

    # Tabelvisning (uden intern scroll)
    tabel_hoejde = (len(page_df) * 35) + 40
    event = st.dataframe(
        page_df[["NAVN", "POSITION", "KLUB", "RATING_AVG", "STATUS", "DATO"]],
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
        height=tabel_hoejde,
        column_config={
            "RATING_AVG": st.column_config.NumberColumn("Snit", format="%.1f"),
            "DATO": st.column_config.DateColumn("Seneste")
        }
    )

    # Diskret paginering
    if total_pages > 1:
        st.write("")
        cp1, cp2, cp3 = st.columns([1, 2, 1])
        with cp1:
            if st.button("← Forrige", disabled=(st.session_state.scout_page <= 1), use_container_width=True):
                st.session_state.scout_page -= 1
                st.rerun()
        with cp2:
            st.markdown(f"<p style='text-align: center; color: gray;'>Side {st.session_state.scout_page} af {total_pages}</p>", unsafe_allow_html=True)
        with cp3:
            if st.button("Næste →", disabled=(st.session_state.scout_page >= total_pages), use_container_width=True):
                st.session_state.scout_page += 1
                st.rerun()

    if len(event.selection.rows) > 0:
        vis_profil(page_df.iloc[event.selection.rows[0]], df, stats_df)
