import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests  # Vigtigt: skal bruges til billed-tjek

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

def vis_spiller_billede(pid, w=100):
    """Henter spillerbillede fra Wyscout CDN."""
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w if resp.status_code == 200 else int(w*0.92))
    except:
        st.image(std, width=int(w*0.92))

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
    historik = full_df[full_df[id_col].astype(str) == str(p_data['ID'])].sort_values('DATO_DT', ascending=True)
    nyeste = historik.iloc[-1]
    
    seneste_dato = hent_vaerdi_robust(nyeste, 'Dato')
    scout_navn = hent_vaerdi_robust(nyeste, 'Scout')

    # Top sektion med Info til venstre og Billede til højre
    head_left, head_right = st.columns([4, 1])
    
    with head_left:
        st.markdown(f"""
            <h2 style='margin-bottom:0;'>{p_data.get('NAVN', 'Ukendt')}</h2>
            <p style='color: gray; font-size: 18px; margin-top:0;'>
                {p_data.get('KLUB', '')} | {p_data.get('POSITION', '')} | Snit: {p_data.get('RATING_AVG', 0)}<br>
                <span style='font-size: 14px;'><b>Seneste rapport: {seneste_dato}</b> {f'| Scout: {scout_navn}' if scout_navn else ''}</span>
            </p>
        """, unsafe_allow_html=True)
    
    with head_right:
        vis_spiller_billede(p_data['ID'], w=110)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Grafik Card"])
    
    with tab1:
        vis_metrikker(nyeste)
        st.write("")
        vis_scout_bokse(nyeste)

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            dato_str = str(hent_vaerdi_robust(row, 'Dato'))
            s_navn = hent_vaerdi_robust(row, 'Scout')
            label = f"Rapport fra {dato_str} (Rating: {hent_vaerdi_robust(row, 'Rating_Avg')})"
            if s_navn: label += f" - Scout: {s_navn}"
            
            with st.expander(label):
                vis_metrikker(row)
                st.write("")
                vis_scout_bokse(row)

    with tab3:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik[find_col(full_df, 'rating_avg')], mode='lines+markers', line_color='#df003b'))
        fig_line.update_layout(height=300, yaxis=dict(range=[1, 6]), margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        if s_df.empty: st.info("Ingen kampdata fundet.")
        else:
            sp_stats = s_df[s_df['PLAYER_WYID'].astype(str) == str(p_data['ID'])].copy()
            cols_to_show = [c for c in sp_stats.columns if c != 'PLAYER_WYID']
            st.dataframe(sp_stats, use_container_width=True, hide_index=True, column_order=cols_to_show)

    with tab5:
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        v = [rens_metrik_vaerdi(hent_vaerdi_robust(nyeste, k)) for k in categories]
        v_closed = v + [v[0]]
        
        col_left, col_mid, col_right = st.columns([1.5, 4, 2.5])
        
        with col_left:
            st.markdown(f"### Værdier\n*{seneste_dato}*")
            if scout_navn: st.caption(f"Scout: {scout_navn}")
            for cat, val in zip(categories, v):
                st.markdown(f"**{cat}:** `{val}`")
        
        with col_mid:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=v_closed, theta=categories + [categories[0]], fill='toself', line_color='#df003b'))
            fig_radar.update_layout(
                polar=dict(
                    gridshape='linear', 
                    radialaxis=dict(visible=True, range=[0, 6], showticklabels=False, gridcolor="lightgray")
                ),
                showlegend=False, height=450, margin=dict(l=40, r=40, t=20, b=20)
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            
        with col_right:
            st.success(f"**Styrker**\n\n{hent_vaerdi_robust(nyeste, 'Styrker') or 'Ingen data'}")
            st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(nyeste, 'Udvikling') or 'Ingen data'}")
            st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(nyeste, 'Vurdering') or 'Ingen data'}")

# --- 3. HOVEDFUNKTION (FORTSÆTTER SOM FØR) ---
