import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests

# --- 1. ROBUSTE HJÆLPEFUNKTIONER ---
def find_col(df, target):
    cols = {str(c).strip().lower(): str(c) for c in df.columns}
    return cols.get(target.strip().lower())

def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def hent_vaerdi_robust(row, col_name):
    row_dict = {str(k).strip().lower(): v for k, v in row.items()}
    return row_dict.get(col_name.strip().lower(), "")

def vis_spiller_billede(pid, w=120):
    """Henter spillerbillede fra Wyscout CDN."""
    pid_clean = str(pid).replace('"', '').replace("'", "").strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except:
        st.image(std, width=w)

def vis_metrikker(row):
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

def vis_scout_bokse(row):
    c1, c2, c3 = st.columns(3)
    with c1: st.success(f"**Styrker**\n\n{hent_vaerdi_robust(row, 'Styrker') or 'Ingen data'}")
    with c2: st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(row, 'Udvikling') or 'Ingen data'}")
    with c3: st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(row, 'Vurdering') or 'Ingen data'}")

# --- 2. PROFIL DIALOG ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df):
    id_col = find_col(full_df, 'id')
    clean_p_id = str(p_data['ID']).replace('"', '').strip()
    historik = full_df[full_df[id_col].astype(str).str.replace('"', '').str.strip() == clean_p_id].sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error("Kunne ikke finde data på denne spiller.")
        return

    nyeste = historik.iloc[-1]
    seneste_dato = hent_vaerdi_robust(nyeste, 'Dato')
    scout_navn = hent_vaerdi_robust(nyeste, 'Scout')

    # Top sektion: Billede til VENSTRE, tekst til HØJRE
    head_col1, head_col2 = st.columns([1, 3])
    with head_col1:
        vis_spiller_billede(clean_p_id, w=120)
    with head_col2:
        st.markdown(f"""
            <h2 style='margin-bottom:0;'>{p_data.get('NAVN', 'Ukendt')}</h2>
            <p style='color: gray; font-size: 18px; margin-top:0;'>
                {p_data.get('KLUB', '')} | {p_data.get('POSITION', '')} | Snit: {p_data.get('RATING_AVG', 0)}<br>
                <span style='font-size: 14px;'><b>Seneste rapport: {seneste_dato}</b> {f'| Scout: {scout_navn}' if scout_navn else ''}</span>
            </p>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Grafik Card"])
    
    with tab1:
        vis_metrikker(nyeste)
        st.write("")
        vis_scout_bokse(nyeste)

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            dato_str = str(hent_vaerdi_robust(row, 'Dato'))
            label = f"Rapport fra {dato_str} (Rating: {hent_vaerdi_robust(row, 'Rating_Avg')})"
            with st.expander(label):
                vis_metrikker(row)
                vis_scout_bokse(row)

    with tab3:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik[find_col(full_df, 'rating_avg')], mode='lines+markers', line_color='#df003b'))
        fig_line.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        if s_df.empty: st.info("Ingen kampdata fundet.")
        else:
            sp_stats = s_df[s_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
            st.dataframe(sp_stats, use_container_width=True, hide_index=True, height=400) # Fast højde for at undgå scroll

    with tab5:
        # Grafik card (Radar) som før...
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        v = [rens_metrik_vaerdi(hent_vaerdi_robust(nyeste, k)) for k in categories]
        v_closed = v + [v[0]]
        c_l, c_m, c_r = st.columns([1.5, 4, 2.5])
        with c_m:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=v_closed, theta=categories + [categories[0]], fill='toself', line_color='#df003b'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=400)
            st.plotly_chart(fig_radar, use_container_width=True)

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    all_data = st.session_state["main_data"]
    stats_df = all_data[4]
    df = all_data[5].copy()

    c_id = find_col(df, 'id')
    c_dato = find_col(df, 'dato')
    c_navn = find_col(df, 'navn')
    c_klub = find_col(df, 'klub')
    c_pos = find_col(df, 'position')
    c_rating = find_col(df, 'rating_avg')
    c_status = find_col(df, 'status')

    df['DATO_DT'] = pd.to_datetime(df[c_dato], errors='coerce')
    df[c_rating] = pd.to_numeric(df[c_rating].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    st.subheader("Scouting Database")
    search = st.text_input("Søg spiller eller klub", placeholder="Søg...", label_visibility="collapsed")
    
    f_df = df.groupby(c_id).tail(1).copy()
    if search:
        f_df = f_df[f_df[c_navn].str.contains(search, case=False, na=False) | f_df[c_klub].str.contains(search, case=False, na=False)]

    # HER RETTES SCROLL-PROBLEMET:
    # Vi sætter height=600 eller lignende, så tabellen fylder skærmen ud.
    event = st.dataframe(
        f_df[[c_navn, c_pos, c_klub, c_rating, c_status, c_dato]],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        height=600 # <--- Dette fjerner scroll i selve containeren
    )

    if len(event.selection.rows) > 0:
        idx = event.selection.rows[0]
        p_row = f_df.iloc[idx]
        vis_profil({'ID': p_row[c_id], 'NAVN': p_row[c_navn], 'KLUB': p_row[c_klub], 'POSITION': p_row[c_pos], 'RATING_AVG': p_row[c_rating]}, df, stats_df)
