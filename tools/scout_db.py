import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

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
    """Viser de tre farvede infobokse."""
    c1, c2, c3 = st.columns(3)
    with c1: st.success(f"**Styrker**\n\n{hent_vaerdi_robust(row, 'Styrker') or 'Ingen data'}")
    with c2: st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(row, 'Udvikling') or 'Ingen data'}")
    with c3: st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(row, 'Vurdering') or 'Ingen data'}")

# --- 2. PROFIL DIALOG ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df):
    st.markdown(f"<div style='text-align: center;'><h2 style='margin-bottom:0;'>{p_data.get('NAVN', 'Ukendt')}</h2>"
                f"<p style='color: gray; font-size: 18px;'>{p_data.get('KLUB', '')} | {p_data.get('POSITION', '')} | Snit: {p_data.get('RATING_AVG', 0)}</p></div>", unsafe_allow_html=True)
    
    id_col = find_col(full_df, 'id')
    historik = full_df[full_df[id_col].astype(str) == str(p_data['ID'])].sort_values('DATO_DT', ascending=True)
    nyeste = historik.iloc[-1]
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Grafik Card"])
    
    with tab1:
        vis_metrikker(nyeste)
        st.write("")
        vis_scout_bokse(nyeste)

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            dato_str = str(hent_vaerdi_robust(row, 'Dato'))
            with st.expander(f"Rapport fra {dato_str} (Rating: {hent_vaerdi_robust(row, 'Rating_Avg')})"):
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
            st.dataframe(sp_stats, use_container_width=True, hide_index=True)

    with tab5:
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        v = [rens_metrik_vaerdi(hent_vaerdi_robust(nyeste, k)) for k in categories]
        v_closed = v + [v[0]]
        
        # Layout: Tal til venstre | Radar i midten | Bokse til højre
        col_left, col_mid, col_right = st.columns([1.5, 4, 2.5])
        
        with col_left:
            st.markdown("### Værdier")
            for cat, val in zip(categories, v):
                st.markdown(f"**{cat}:** `{val}`")
        
        with col_mid:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=v_closed, theta=categories + [categories[0]], fill='toself', line_color='#df003b'))
            fig_radar.update_layout(
                polar=dict(
                    gridshape='linear', 
                    radialaxis=dict(
                        visible=True, 
                        range=[0, 6], 
                        showticklabels=False, # Skjuler tal på aksen, men viser linjer
                        gridcolor="lightgray"
                    )
                ),
                showlegend=False, height=450, margin=dict(l=40, r=40, t=20, b=20)
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            
        with col_right:
            st.success(f"**Styrker**\n\n{hent_vaerdi_robust(nyeste, 'Styrker') or 'Ingen data'}")
            st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(nyeste, 'Udvikling') or 'Ingen data'}")
            st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(nyeste, 'Vurdering') or 'Ingen data'}")

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    data = st.session_state["main_data"]
    stats_df, df = data[4], data[5].copy()

    c_id, c_dato, c_navn, c_klub, c_pos, c_rating = find_col(df, 'id'), find_col(df, 'dato'), find_col(df, 'navn'), find_col(df, 'klub'), find_col(df, 'position'), find_col(df, 'rating_avg')
    c_status = find_col(df, 'status')

    df['DATO_DT'] = pd.to_datetime(df[c_dato], errors='coerce')
    df[c_rating] = pd.to_numeric(df[c_rating].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    df = df.sort_values('DATO_DT')

    st.markdown("<p style='font-size: 14px; font-weight: bold; margin-bottom: 20px;'>Scouting Database</p>", unsafe_allow_html=True)

    # Filter
    search = st.text_input("Søg", placeholder="Søg...", label_visibility="collapsed")
    f_df = df.groupby(c_id).tail(1).copy()
    
    if search:
        f_df = f_df[f_df[c_navn].str.contains(search, case=False, na=False) | f_df[c_klub].str.contains(search, case=False, na=False)]

    page_display = f_df.rename(columns={c_navn: "NAVN", c_pos: "POSITION", c_klub: "KLUB", c_rating: "RATING_AVG", c_status: "STATUS", c_dato: "DATO"})

    event = st.dataframe(
        page_display[["NAVN", "POSITION", "KLUB", "RATING_AVG", "STATUS", "DATO"]],
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
        column_config={"RATING_AVG": st.column_config.NumberColumn("Snit", format="%.1f")}
    )

    if len(event.selection.rows) > 0:
        row_idx = event.selection.rows[0]
        p_data = {'ID': f_df.iloc[row_idx][c_id], 'NAVN': f_df.iloc[row_idx][c_navn], 'KLUB': f_df.iloc[row_idx][c_klub], 'POSITION': f_df.iloc[row_idx][c_pos], 'RATING_AVG': f_df.iloc[row_idx][c_rating]}
        vis_profil(p_data, df, stats_df)
