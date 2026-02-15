import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests

# --- 1. HJÆLPEFUNKTIONER (RENS OG DATA) ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def hent_vaerdi_robust(row, col_name):
    col_upper = col_name.strip().upper()
    val = row.get(col_upper, "")
    return "" if pd.isna(val) else val

def map_position(row):
    """Mapper positioner baseret på tal (POS) eller koder (ROLECODE3)."""
    db_pos = str(row.get('POSITION', '')).strip().split('.')[0]
    csv_pos = str(row.get('POS', '')).strip().split('.')[0]
    role_raw = str(row.get('ROLECODE3', '')).strip().upper()
    
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    
    role_map = {
        "GKP": "Målmand", "DEF": "Forsvarsspiller",
        "MID": "Midtbane", "FWD": "Angriber"
    }

    if csv_pos in pos_dict: return pos_dict[csv_pos]
    if db_pos in pos_dict: return pos_dict[db_pos]
    if len(db_pos) > 2 and db_pos.upper() not in ["NAN", "NONE", "UKENDT"] + list(role_map.keys()):
        return db_pos
    return role_map.get(role_raw, "Ukendt")

def vis_spiller_billede(pid, w=110):
    pid_clean = str(pid).split('.')[0].replace('"', '').replace("'", "").strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except:
        st.image(std, width=w)

# --- 2. HJÆLPEFUNKTIONER (VISUELT LAYOUT) ---
def vis_metrikker(row):
    """Viser de 8 kerne-metrikker i pæne kolonner."""
    m_cols = st.columns(4)
    metrics = [
        ("Beslutsomhed", "BESLUTSOMHED"), ("Fart", "FART"), 
        ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
        ("Udholdenhed", "UDHOLDENHED"), ("Lederegenskaber", "LEDEREGENSKABER"), 
        ("Teknik", "TEKNIK"), ("Spilintelligens", "SPILINTELLIGENS")
    ]
    for i, (label, col) in enumerate(metrics):
        val = rens_metrik_vaerdi(row.get(col, 0))
        m_cols[i % 4].metric(label, f"{val}")

def vis_bokse_kolonner(row):
    """Viser Styrker, Udvikling og Vurdering i 3 kolonner."""
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.success(f"**Styrker**\n\n{row.get('STYRKER', 'Ingen data')}")
    with c2: st.warning(f"**Udvikling**\n\n{row.get('UDVIKLING', 'Ingen data')}")
    with c3: st.info(f"**Vurdering**\n\n{row.get('VURDERING', 'Ingen data')}")

def vis_bokse_lodret(row):
    """Viser Styrker, Udvikling og Vurdering under hinanden."""
    st.success(f"**Styrker**\n\n{row.get('STYRKER', '-')}")
    st.warning(f"**Udvikling**\n\n{row.get('UDVIKLING', '-')}")
    st.info(f"**Vurdering**\n\n{row.get('VURDERING', '-')}")

# --- 3. PROFIL DIALOG ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df):
    clean_p_id = str(p_data['PLAYER_WYID']).split('.')[0].strip()
    historik = full_df[full_df['PLAYER_WYID'].astype(str) == clean_p_id].sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error("Data ikke fundet.")
        return

    nyeste = historik.iloc[-1]
    seneste_dato = hent_vaerdi_robust(nyeste, 'DATO')
    scout_navn = hent_vaerdi_robust(nyeste, 'SCOUT')
    rating_col = 'RATING_AVG'

    head_col1, head_col2 = st.columns([1, 4])
    with head_col1:
        vis_spiller_billede(clean_p_id, w=115)
    with head_col2:
        st.markdown(f"<h2 style='margin-top:0;'>{p_data.get('NAVN', 'Ukendt')}</h2>", unsafe_allow_html=True)
        st.markdown(f"**{p_data.get('KLUB', '')}** | {p_data.get('POSITION', '')} | Snit: {p_data.get('RATING_AVG', 0)}")
        st.caption(f"Seneste rapport: {seneste_dato} | Scout: {scout_navn}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radarchart"])
    
    with tab1:
        vis_metrikker(nyeste)
        vis_bokse_kolonner(nyeste)

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            h_scout = hent_vaerdi_robust(row, 'SCOUT')
            h_dato = hent_vaerdi_robust(row, 'DATO')
            h_rate = hent_vaerdi_robust(row, 'RATING_AVG')
            with st.expander(f"Rapport: {h_dato} | Scout: {h_scout} | Rating: {h_rate}"):
                vis_metrikker(row)
                vis_bokse_kolonner(row)

    with tab3:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik[rating_col], mode='markers+lines', line_color='#df003b'))
        fig_line.update_layout(height=450, yaxis=dict(range=[1, 6], title="Rating"), xaxis=dict(title="Dato"))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        display_stats = s_df[s_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
        if not display_stats.empty:
            st.dataframe(display_stats.drop(columns=['PLAYER_WYID'], errors='ignore'), use_container_width=True, hide_index=True)
        else:
            st.info("Ingen statistisk data fundet.")

    with tab5:
        cl, cm, cr = st.columns([1.5, 4, 2.5])
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        cols = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        v_closed = v + [v[0]]
        
        with cl:
            st.markdown(f"*{seneste_dato}*")
            for cat, val in zip(categories, v):
                color = "#df003b" if val >= 4 else "#555"
                st.markdown(f"**{cat}:** <span style='color:{color};'>{val}</span>", unsafe_allow_html=True)
        with cm:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=v_closed, 
                theta=categories + [categories[0]], 
                fill='toself', 
                line_color='#df003b',
                fillcolor='rgba(223, 0, 59, 0.3)',
                marker=dict(size=8)
            ))
            
            fig_radar.update_layout(
                polar=dict(
                    gridshape='linear',  # DETTE GØR DEN 8-KANTET
                    radialaxis=dict(
                        visible=True, 
                        range=[0, 6], 
                        
                        gridcolor="lightgrey",
                        showticklabels=True
                    ),
                    angularaxis=dict(
                        gridcolor="lightgrey",
                        rotation=90,
                        direction="clockwise"
                    )
                ), 
                showlegend=False, 
                height=450,
                margin=dict(l=60, r=60, t=20, b=20)
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        with cr:
            vis_bokse_lodret(nyeste)

# --- 4. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    _, _, _, spillere_df, stats_df, scout_df = st.session_state["main_data"]

    # Ultra-rens
    scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    s_info = spillere_df[['PLAYER_WYID', 'POS', 'ROLECODE3']].drop_duplicates('PLAYER_WYID')
    df = scout_df.merge(s_info, on='PLAYER_WYID', how='left')
    
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    df = df.sort_values('DATO_DT')

    st.subheader("Scouting Database")
    col_s, col_p = st.columns([4, 1.2])
    with col_s:
        search = st.text_input("Søg...", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
    with col_p:
        with st.popover("Filtrér", use_container_width=True):
            valgt_status = st.multiselect("Status", options=sorted(df['STATUS'].dropna().unique()))
            valgt_pos = st.multiselect("Position", options=sorted(df['POSITION_VISNING'].unique()))
            rating_range = st.slider("Rating", 0.0, 5.0, (0.0, 5.0), 0.1)

    f_df = df.groupby('PLAYER_WYID').tail(1).copy()
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]
    if valgt_status: f_df = f_df[f_df['STATUS'].isin(valgt_status)]
    if valgt_pos: f_df = f_df[f_df['POSITION_VISNING'].isin(valgt_pos)]
    f_df = f_df[(f_df['RATING_AVG'] >= rating_range[0]) & (f_df['RATING_AVG'] <= rating_range[1])]

    vis_cols = ['NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'DATO', 'SCOUT']
    event = st.dataframe(
        f_df[vis_cols], use_container_width=True, hide_index=True, 
        on_select="rerun", selection_mode="single-row", height=700,
        column_config={"RATING_AVG": st.column_config.NumberColumn("Rating", format="%.1f")}
    )

    if len(event.selection.rows) > 0:
        idx = event.selection.rows[0]
        p_row = f_df.iloc[idx]
        vis_profil({
            'PLAYER_WYID': p_row['PLAYER_WYID'], 'NAVN': p_row['NAVN'], 'KLUB': p_row['KLUB'], 
            'POSITION': p_row['POSITION_VISNING'], 'RATING_AVG': p_row['RATING_AVG']
        }, df, stats_df)

    with st.expander("🛠️ Debug: ID-Match Kontrol"):
        mangler = f_df[f_df['POS'].isna() & f_df['ROLECODE3'].isna()]
        if not mangler.empty:
            st.warning(f"Der er {len(mangler)} spillere uden match i players.csv")
            st.dataframe(mangler[['PLAYER_WYID', 'NAVN']])
        else:
            st.success("Alle matchet korrekt.")
