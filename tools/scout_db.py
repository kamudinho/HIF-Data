import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- 1. ROBUSTE HJÆLPEFUNKTIONER ---
def find_col(df, target):
    """Finder kolonne uanset store/små bogstaver og mellemrum."""
    cols = {str(c).strip().lower(): str(c) for c in df.columns}
    return cols.get(target.strip().lower())

def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def hent_vaerdi_robust(row, col_name):
    """Henter værdi fra en række (Series) uanset casing på key."""
    row_dict = {str(k).strip().lower(): v for k, v in row.items()}
    return row_dict.get(col_name.strip().lower(), 0)

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
    # Setup basis-info
    navn = p_data.get('NAVN', 'Ukendt')
    klub = p_data.get('KLUB', '')
    pos = p_data.get('POSITION', '')
    snit = p_data.get('RATING_AVG', 0)

    st.markdown(f"<div style='text-align: center;'><h2 style='margin-bottom:0;'>{navn}</h2>"
                f"<p style='color: gray; font-size: 18px;'>{klub} | {pos} | Snit: {snit}</p></div>", unsafe_allow_html=True)
    
    # Hent historik baseret på ID
    id_col = find_col(full_df, 'id')
    historik = full_df[full_df[id_col].astype(str) == str(p_data['ID'])].sort_values('DATO_DT', ascending=True)
    nyeste = historik.iloc[-1]
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Grafik Card"])
    
    with tab1:
        vis_metrikker(nyeste)
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Styrker**\n\n{hent_vaerdi_robust(nyeste, 'Styrker') or 'Ingen data'}")
        with c2: st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(nyeste, 'Udvikling') or 'Ingen data'}")
        with c3: st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(nyeste, 'Vurdering') or 'Ingen data'}")

    with tab2:
        # VISER ALLE TIDLIGERE RAPPORTER
        for _, row in historik.iloc[::-1].iterrows():
            dato_str = str(hent_vaerdi_robust(row, 'Dato'))
            r_snit = hent_vaerdi_robust(row, 'Rating_Avg')
            with st.expander(f"Rapport fra {dato_str} (Rating: {r_snit})"):
                vis_metrikker(row)
                st.write(f"**Vurdering:** {hent_vaerdi_robust(row, 'Vurdering')}")

    with tab3:
        # UDVIKLING OVER TID (LINJEGRAF)
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik[find_col(full_df, 'rating_avg')], mode='lines+markers', line_color='#df003b'))
        fig_line.update_layout(height=300, yaxis=dict(range=[1, 6]), margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        # WYISCOUT STATS
        if s_df.empty: 
            st.info("Ingen kampdata fundet i systemet.")
        else:
            sp_stats = s_df[s_df['PLAYER_WYID'].astype(str) == str(p_data['ID'])].copy()
            if not sp_stats.empty:
                st.dataframe(sp_stats, use_container_width=True, hide_index=True)
            else:
                st.info("Ingen Wyscout data for denne spiller ID.")

    with tab5:
        # RADAR GRAFIK (1-6 Skala, ingen tal på akser)
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        v = [rens_metrik_vaerdi(hent_vaerdi_robust(nyeste, k)) for k in categories]
        v.append(v[0])
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=v, theta=categories + [categories[0]], fill='toself', line_color='#df003b'))
        fig_radar.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=False, range=[0, 6])),
            showlegend=False, height=450, margin=dict(l=60, r=60, t=40, b=40)
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        st.markdown(f"<div style='text-align: center; background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #ddd;'><b>Vurdering:</b><br>{hent_vaerdi_robust(nyeste, 'Vurdering')}</div>", unsafe_allow_html=True)

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    # Hent data fra session_state
    data = st.session_state["main_data"]
    stats_df = data[4]
    df = data[5].copy()

    # Find kolonner
    c_id = find_col(df, 'id')
    c_dato = find_col(df, 'dato')
    c_navn = find_col(df, 'navn')
    c_klub = find_col(df, 'klub')
    c_pos = find_col(df, 'position')
    c_rating = find_col(df, 'rating_avg')
    c_status = find_col(df, 'status')

    if not all([c_id, c_dato, c_rating]):
        st.error("Fejl: Kunne ikke læse nødvendige kolonner (ID, Dato, Rating). Tjek CSV-filen.")
        return

    # Forbered datoer og ratings
    df['DATO_DT'] = pd.to_datetime(df[c_dato], errors='coerce')
    df[c_rating] = pd.to_numeric(df[c_rating].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    df = df.sort_values('DATO_DT')

    st.markdown("<p style='font-size: 14px; font-weight: bold; margin-bottom: 20px;'>Scouting Database</p>", unsafe_allow_html=True)

    # Filtrering
    c1, c2 = st.columns([3, 1])
    with c1:
        search = st.text_input("Søg", placeholder="Søg på navn eller klub...", label_visibility="collapsed")
    with c2:
        with st.popover("Filtre"):
            f_pos_opt = sorted(df[c_pos].dropna().unique().tolist()) if c_pos else []
            f_pos = st.multiselect("Positioner", options=f_pos_opt)
            f_rating = st.slider("Rating", 1.0, 6.0, (1.0, 6.0), step=0.1)

    # Find seneste rapporter (Én række pr. spiller til tabellen)
    f_df = df.groupby(c_id).tail(1).copy()
    
    if search:
        f_df = f_df[f_df[c_navn].str.contains(search, case=False, na=False) | 
                    f_df[c_klub].str.contains(search, case=False, na=False)]
    if f_pos:
        f_df = f_df[f_df[c_pos].isin(f_pos)]
    
    f_df = f_df[(f_df[c_rating] >= f_rating[0]) & (f_df[c_rating] <= f_rating[1])]

    # Paginering
    items_per_page = 20
    total_pages = max(1, int(np.ceil(len(f_df) / items_per_page)))
    if 'scout_page' not in st.session_state: st.session_state.scout_page = 1
    start_idx = (st.session_state.scout_page - 1) * items_per_page
    page_df = f_df.iloc[start_idx : start_idx + items_per_page]

    # Visningstabel
    display_cols = {c_navn: "NAVN", c_pos: "POSITION", c_klub: "KLUB", c_rating: "RATING_AVG", c_status: "STATUS", c_dato: "DATO"}
    page_display = page_df[list(display_cols.keys())].rename(columns=display_cols)

    tabel_hoejde = (len(page_df) * 35) + 45
    event = st.dataframe(
        page_display, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
        height=tabel_hoejde,
        column_config={"RATING_AVG": st.column_config.NumberColumn("Snit", format="%.1f")}
    )

    # Sidevælger
    if total_pages > 1:
        st.write("")
        cp1, cp2, cp3 = st.columns([1, 2, 1])
        with cp1:
            if st.button("← Forrige", disabled=(st.session_state.scout_page <= 1)):
                st.session_state.scout_page -= 1
                st.rerun()
        with cp2:
            st.markdown(f"<p style='text-align: center; color: gray;'>Side {st.session_state.scout_page} af {total_pages}</p>", unsafe_allow_html=True)
        with cp3:
            if st.button("Næste →", disabled=(st.session_state.scout_page >= total_pages)):
                st.session_state.scout_page += 1
                st.rerun()

    # Åbn profil
    if len(event.selection.rows) > 0:
        row_idx = event.selection.rows[0]
        p_data = {
            'ID': page_df.iloc[row_idx][c_id],
            'NAVN': page_df.iloc[row_idx][c_navn],
            'KLUB': page_df.iloc[row_idx][c_klub],
            'POSITION': page_df.iloc[row_idx][c_pos],
            'RATING_AVG': page_df.iloc[row_idx][c_rating]
        }
        vis_profil(p_data, df, stats_df)
