import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- 1. HJÆLPEFUNKTIONER TIL DATA ---
def rens_metrik_vaerdi(val):
    """Sikrer at værdier fra CSV bliver til tal."""
    try:
        if pd.isna(val) or str(val).strip() == "": 
            return 0
        return int(float(str(val).replace(',', '.')))
    except:
        return 0

def hent_vaerdi_robust(row, col_name):
    """Tjekker både 'Beslutsomhed' og 'BESLUTSOMHED' i rækken."""
    return row.get(col_name, row.get(col_name.upper(), 0))

def vis_metrikker(row):
    """Viser de 8 metrikker i toppen af profilen."""
    m_cols = st.columns(4)
    metrics = [
        ("Beslutsomhed", "Beslutsomhed"), ("Fart", "Fart"), 
        ("Aggresivitet", "Aggresivitet"), ("Attitude", "Attitude"),
        ("Udholdenhed", "Udholdenhed"), ("Lederegenskaber", "Lederegenskaber"), 
        ("Teknik", "Teknik"), ("Spilintelligens", "Spilintelligens")
    ]
    for i, (label, col) in enumerate(metrics):
        val = rens_metrik_vaerdi(hent_vaerdi_robust(row, col))
        m_cols[i % 4].metric(label, f"{val}")

# --- 2. PROFIL DIALOG (POP-UP) ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df):
    st.markdown(f"""
        <div style='text-align: center;'>
            <h2 style='margin-bottom: 0;'>{p_data['NAVN']}</h2>
            <p style='font-size: 18px; color: gray;'>{p_data['KLUB']} | {p_data['POSITION']} | Snit: {p_data['RATING_AVG']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Hent historik baseret på ID
    historik = full_df[full_df['ID'].astype(str) == str(p_data['ID'])].sort_values('DATO_DT', ascending=True)
    nyeste = historik.iloc[-1]
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Grafik Card"])
    
    with tab1:
        vis_metrikker(nyeste)
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Styrker**\n\n{nyeste.get('Styrker', 'Ingen data')}")
        with c2: st.warning(f"**Udvikling**\n\n{nyeste.get('Udvikling', 'Ingen data')}")
        with c3: st.info(f"**Vurdering**\n\n{nyeste.get('Vurdering', 'Ingen data')}")

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            with st.expander(f"Rapport fra {row['Dato']} (Rating: {row['Rating_Avg']})"):
                vis_metrikker(row)

    with tab3:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['Dato'], y=historik['Rating_Avg'], mode='lines+markers', line_color='#df003b'))
        fig_line.update_layout(height=300, yaxis=dict(range=[1, 6]), margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        if s_df.empty: 
            st.info("Ingen kampdata fundet.")
        else:
            sp_stats = s_df[s_df['PLAYER_WYID'].astype(str) == str(p_data['ID'])].copy()
            st.dataframe(sp_stats, use_container_width=True, hide_index=True)

    with tab5:
        # RADAR UDEN TAL PÅ AKSERNE
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        v = [rens_metrik_vaerdi(hent_vaerdi_robust(nyeste, k)) for k in categories]
        v.append(v[0])
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=v, 
            theta=categories + [categories[0]], 
            fill='toself', 
            line_color='#df003b',
            hoverinfo='r+theta'
        ))
        
        fig_radar.update_layout(
            polar=dict(
                gridshape='linear', 
                radialaxis=dict(
                    visible=False, # Skjuler alle tal og tick-marks
                    range=[0, 6]
                ),
                angularaxis=dict(tickfont=dict(size=11))
            ),
            showlegend=False, height=450, margin=dict(l=60, r=60, t=40, b=40)
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        
        st.markdown(f"""
            <div style='text-align: center; background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #ddd;'>
                <p style='margin:0; font-weight:bold;'>Vurdering:</p>
                <p style='margin:0;'>{nyeste.get('Vurdering', 'N/A')}</p>
            </div>
        """, unsafe_allow_html=True)

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    data = st.session_state["main_data"]
    stats_df = data[4]
    df = data[5].copy()

    if df.empty:
        st.warning("Databasen er tom.")
        return

    # Forbered data
    df.columns = [c.strip() for c in df.columns]
    df['DATO_DT'] = pd.to_datetime(df['Dato'], errors='coerce')
    df = df.sort_values('DATO_DT')

    st.markdown("<p style='font-size: 14px; font-weight: bold; margin-bottom: 20px;'>Scouting Database</p>", unsafe_allow_html=True)

    # Filtrering
    c1, c2 = st.columns([3, 1])
    with c1:
        search = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
    with c2:
        with st.popover("Filtre"):
            f_pos = st.multiselect("Positioner", options=sorted(df['Position'].dropna().unique().tolist()))
            f_rating = st.slider("Rating", 1.0, 6.0, (1.0, 6.0), step=0.1)

    # Find seneste rapport
    f_df = df.groupby('ID').tail(1).copy()
    
    if search:
        f_df = f_df[f_df['Navn'].str.contains(search, case=False, na=False) | 
                    f_df['Klub'].str.contains(search, case=False, na=False)]
    if f_pos:
        f_df = f_df[f_df['Position'].isin(f_pos)]
    
    f_df = f_df[(f_df['Rating_Avg'].astype(float) >= f_rating[0]) & 
                (f_df['Rating_Avg'].astype(float) <= f_rating[1])]

    # Paginering
    items_per_page = 20
    total_pages = max(1, int(np.ceil(len(f_df) / items_per_page)))
    if 'scout_page' not in st.session_state: st.session_state.scout_page = 1
    if st.session_state.scout_page > total_pages: st.session_state.scout_page = total_pages

    start_idx = (st.session_state.scout_page - 1) * items_per_page
    page_df = f_df.iloc[start_idx : start_idx + items_per_page]

    # Omdøb til visning
    page_df_display = page_df.rename(columns={
        "Navn": "NAVN", "Position": "POSITION", "Klub": "KLUB", 
        "Rating_Avg": "RATING_AVG", "Status": "STATUS", "Dato": "DATO"
    })

    tabel_hoejde = (len(page_df) * 35) + 45
    event = st.dataframe(
        page_df_display[["NAVN", "POSITION", "KLUB", "RATING_AVG", "STATUS", "DATO"]],
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
        height=tabel_hoejde,
        column_config={
            "RATING_AVG": st.column_config.NumberColumn("Snit", format="%.1f"),
            "DATO": st.column_config.DateColumn("Seneste")
        }
    )

    # Sidevælger
    if total_pages > 1:
        st.write("")
        cp1, cp2, cp3 = st.columns([1, 2, 1])
        with cp1:
            if st.button("← Forrige", disabled=(st.session_state.scout_page <= 1), use_container_width=True):
                st.session_state.scout_page -= 1
                st.rerun()
        with cp2:
            st.markdown(f"<p style='text-align: center; color: gray; padding-top: 5px;'>Side {st.session_state.scout_page} af {total_pages}</p>", unsafe_allow_html=True)
        with cp3:
            if st.button("Næste →", disabled=(st.session_state.scout_page >= total_pages), use_container_width=True):
                st.session_state.scout_page += 1
                st.rerun()

    if len(event.selection.rows) > 0:
        valgt_idx = event.selection.rows[0]
        spiller_data = page_df_display.iloc[valgt_idx]
        vis_profil(spiller_data, df, stats_df)
