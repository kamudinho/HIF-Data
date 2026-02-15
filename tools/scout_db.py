import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests

# --- 1. HJÆLPEFUNKTIONER ---
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

def vis_spiller_billede(pid, w=110):
    pid_clean = str(pid).split('.')[0].replace('"', '').replace("'", "").strip()
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

# --- 2. PROFIL DIALOG ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df):
    id_col = find_col(full_df, 'id')
    clean_p_id = str(p_data['ID']).split('.')[0].replace('"', '').strip()
    historik = full_df[full_df[id_col].astype(str).str.contains(clean_p_id, na=False)].sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error("Ingen data fundet.")
        return

    nyeste = historik.iloc[-1]
    seneste_dato = hent_vaerdi_robust(nyeste, 'Dato')
    scout_navn = hent_vaerdi_robust(nyeste, 'Scout')

    # Top sektion: Billede til VENSTRE, Info til HØJRE
    head_left, head_right = st.columns([1, 4])
    with head_left:
        vis_spiller_billede(clean_p_id, w=115)
    with head_right:
        st.markdown(f"<h2 style='margin-top:0;'>{p_data.get('NAVN', 'Ukendt')}</h2>", unsafe_allow_html=True)
        st.markdown(f"**{p_data.get('KLUB', '')}** | {p_data.get('POSITION', '')} | Snit: {p_data.get('RATING_AVG', 0)}")
        st.caption(f"Seneste rapport: {seneste_dato} | Scout: {scout_navn}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Grafik Card"])
    
    with tab1:
        vis_metrikker(nyeste)
        st.write("")
        st.success(f"**Styrker**\n\n{hent_vaerdi_robust(nyeste, 'Styrker')}")
        st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(nyeste, 'Udvikling')}")
        st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(nyeste, 'Vurdering')}")

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            label = f"Rapport: {hent_vaerdi_robust(row, 'Dato')} | Scout: {hent_vaerdi_robust(row, 'Scout')}"
            with st.expander(label):
                vis_metrikker(row)
                st.success(f"**Styrker**\n\n{hent_vaerdi_robust(row, 'Styrker')}")
                st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(row, 'Udvikling')}")
                st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(row, 'Vurdering')}")

    with tab3:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik[find_col(full_df, 'rating_avg')], mode='lines+markers', line_color='#df003b'))
        fig_line.update_layout(height=300, yaxis=dict(range=[1, 6]))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        sp_stats = s_df[s_df['PLAYER_WYID'].astype(str).str.contains(clean_p_id, na=False)].copy()
        if not sp_stats.empty:
            st.dataframe(sp_stats.drop(columns=['PLAYER_WYID']), use_container_width=True, hide_index=True)

    with tab5:
        # Layout: Værdier | Radar | BOKSE STABLET
        c_v, c_r, c_b = st.columns([1.5, 3.5, 2.5])
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        
        with c_v:
            st.markdown(f"### Værdier\n*{seneste_dato}*")
            for cat in categories:
                val = rens_metrik_vaerdi(hent_vaerdi_robust(nyeste, cat))
                st.markdown(f"**{cat}:** `{val}`")
        with c_r:
            v = [rens_metrik_vaerdi(hent_vaerdi_robust(nyeste, k)) for k in categories]
            v_closed = v + [v[0]]
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=v_closed, theta=categories + [categories[0]], fill='toself', line_color='#df003b'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=400)
            st.plotly_chart(fig_radar, use_container_width=True)
        with c_b:
            # HER STABLES BOKSENE LODRET
            st.success(f"**Styrker**\n\n{hent_vaerdi_robust(nyeste, 'Styrker') or 'Ingen data'}")
            st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(nyeste, 'Udvikling') or 'Ingen data'}")
            st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(nyeste, 'Vurdering') or 'Ingen data'}")

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    all_data = st.session_state["main_data"]
    stats_df = all_data[4]
    df = all_data[5].copy()

    c_id, c_dato, c_navn, c_klub, c_pos, c_rating, c_status, c_scout = [find_col(df, x) for x in ['id', 'dato', 'navn', 'klub', 'position', 'rating_avg', 'status', 'scout']]

    df['DATO_DT'] = pd.to_datetime(df[c_dato], errors='coerce')
    df[c_rating] = pd.to_numeric(df[c_rating].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    df = df.sort_values('DATO_DT')

    st.subheader("Scouting Database")

    # POP-OVER FILTER (Som vi aftalte!)
    col_s, col_p = st.columns([4, 1])
    with col_s:
        search = st.text_input("Søg...", label_visibility="collapsed")
    with col_p:
        with st.popover("Filtrér"):
            # .dropna() fixer din TypeError
            status_opts = sorted([str(x) for x in df[c_status].dropna().unique()])
            valgt_status = st.multiselect("Status", options=status_opts)
            scout_opts = sorted([str(x) for x in df[c_scout].dropna().unique()])
            valgt_scout = st.multiselect("Scout", options=scout_opts)

    f_df = df.groupby(c_id).tail(1).copy()
    if search: f_df = f_df[f_df[c_navn].str.contains(search, case=False, na=False) | f_df[c_klub].str.contains(search, case=False, na=False)]
    if valgt_status: f_df = f_df[f_df[c_status].astype(str).isin(valgt_status)]
    if valgt_scout: f_df = f_df[f_df[c_scout].astype(str).isin(valgt_scout)]

    disp_cols = [c_navn, c_pos, c_klub, c_rating, c_status, c_dato, c_scout]
    
    # HØJ HEIGHT fjerner scroll i tabellen
    event = st.dataframe(
        f_df[disp_cols],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        height=1000, 
        column_config={c_rating: st.column_config.NumberColumn("Rating", format="%.1f")}
    )

    if len(event.selection.rows) > 0:
        idx = event.selection.rows[0]
        p_row = f_df.iloc[idx]
        vis_profil({'ID': p_row[c_id], 'NAVN': p_row[c_navn], 'KLUB': p_row[c_klub], 'POSITION': p_row[c_pos], 'RATING_AVG': p_row[c_rating]}, df, stats_df)
