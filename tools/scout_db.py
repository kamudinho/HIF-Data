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
    val = row_dict.get(col_name.strip().lower(), "")
    return "" if pd.isna(val) else val

def map_position(row):
    # 1. Hent rå værdier og rens dem
    # Vi tjekker både 'Position' (fra din database) og 'POS' (fra players.csv)
    db_text = str(hent_vaerdi_robust(row, 'Position')).strip()
    pos_raw = str(hent_vaerdi_robust(row, 'POS')).strip().split('.')[0]
    role_raw = str(hent_vaerdi_robust(row, 'ROLECODE3')).strip().upper()
    
    # Ordbog for tal (1-11)
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    
    # Ordbog for de rå koder vi ser på dit billede
    role_map = {
        "GKP": "Målmand",
        "DEF": "Forsvarsspiller",
        "MID": "Midtbane",
        "FWD": "Angriber"
    }

    # --- PRIORITET 1: Tjek efter tal (fra begge kilder) ---
    if pos_raw in pos_dict:
        return pos_dict[pos_raw]
    
    db_pos_digit = db_text.split('.')[0]
    if db_pos_digit in pos_dict:
        return pos_dict[db_pos_digit]

    # --- PRIORITET 2: Hvis der er skrevet specifik tekst (f.eks. "Stopper" eller "Fisker") ---
    # Vi ignorerer koderne DEF, MID osv. her, da de håndteres i næste step
    if len(db_text) > 2 and db_text.upper() not in ["NAN", "NONE", "UKENDT"] + list(role_map.keys()):
        if not db_pos_digit.isdigit():
            return db_text

    # --- PRIORITET 3: Oversæt de rå koder (DEF -> Forsvarsspiller) ---
    if role_raw in role_map:
        return role_map[role_raw]
        
    return "-"
    
# --- VISNINGSFUNKTIONER ---
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

def vis_bokse_lodret(row):
    st.success(f"**Styrker**\n\n{hent_vaerdi_robust(row, 'Styrker') or 'Ingen data'}")
    st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(row, 'Udvikling') or 'Ingen data'}")
    st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(row, 'Vurdering') or 'Ingen data'}")

def vis_bokse_kolonner(row):
    c1, c2, c3 = st.columns(3)
    with c1: st.success(f"**Styrker**\n\n{hent_vaerdi_robust(row, 'Styrker') or 'Ingen data'}")
    with c2: st.warning(f"**Udvikling**\n\n{hent_vaerdi_robust(row, 'Udvikling') or 'Ingen data'}")
    with c3: st.info(f"**Vurdering**\n\n{hent_vaerdi_robust(row, 'Vurdering') or 'Ingen data'}")

# --- 2. PROFIL DIALOG (MED ALLE TABS) ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df):
    id_col = find_col(full_df, 'id')
    clean_p_id = str(p_data['ID']).split('.')[0].strip()
    
    # Hent historikken for spilleren
    historik = full_df[full_df[id_col].astype(str).str.contains(clean_p_id, na=False)].sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error("Data ikke fundet.")
        return

    nyeste = historik.iloc[-1]
    seneste_dato = hent_vaerdi_robust(nyeste, 'Dato')
    scout_navn = hent_vaerdi_robust(nyeste, 'Scout')

    # Header sektion
    head_col1, head_col2 = st.columns([1, 4])
    with head_col1:
        vis_spiller_billede(clean_p_id, w=115)
    with head_col2:
        st.markdown(f"<h2 style='margin-top:0;'>{p_data.get('NAVN', 'Ukendt')}</h2>", unsafe_allow_html=True)
        st.markdown(f"**{p_data.get('KLUB', '')}** | {p_data.get('POSITION', '')} | Snit: {p_data.get('RATING_AVG', 0)}")
        st.caption(f"Seneste rapport: {seneste_dato} | Scout: {scout_navn}")

    # Tabs sektion
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radarchart"])
    
    with tab1:
        vis_metrikker(nyeste)
        vis_bokse_kolonner(nyeste)

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            h_scout = hent_vaerdi_robust(row, 'Scout')
            h_dato = hent_vaerdi_robust(row, 'Dato')
            h_rate = hent_vaerdi_robust(row, 'Rating_Avg')
            with st.expander(f"Rapport: {h_dato} | Scout: {h_scout} | Rating: {h_rate}"):
                vis_metrikker(row)
                vis_bokse_kolonner(row)

    with tab3:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik[find_col(full_df, 'rating_avg')], mode='markers+lines', line_color='#df003b'))
        fig_line.update_layout(height=450, yaxis=dict(range=[1, 6]), title="Rating over tid")
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        display_stats = s_df[s_df['PLAYER_WYID'].astype(str).str.contains(clean_p_id, na=False)].copy()
        if not display_stats.empty:
            st.dataframe(display_stats.drop(columns=['PLAYER_WYID'], errors='ignore'), use_container_width=True, hide_index=True)
        else:
            st.info("Ingen statistisk data fundet for denne spiller.")

    with tab5:
        cl, cm, cr = st.columns([1.5, 4, 2.5])
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        v = [rens_metrik_vaerdi(hent_vaerdi_robust(nyeste, k)) for k in categories]
        v_closed = v + [v[0]]
        
        with cl:
            st.markdown(f"*{seneste_dato}*")
            st.caption(f"Scout: {scout_navn}")
            for cat, val in zip(categories, v):
                st.markdown(f"**{cat}:** `{val}`")
        with cm:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=v_closed, theta=categories + [categories[0]], fill='toself', line_color='#df003b'))
            fig_radar.update_layout(
                polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6], showticklabels=False)), 
                showlegend=False, height=450
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        with cr:
            vis_bokse_lodret(nyeste)

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet i session_state.")
        return
    
    all_data = st.session_state["main_data"]
    players_df = all_data[0].copy() 
    stats_df = all_data[4].copy()   
    db_df = all_data[5].copy()      

    c_id = find_col(db_df, 'id')
    p_id = find_col(players_df, 'player_wyid') or 'PLAYER_WYID'

    # ID RENSNING OG MERGE
    if p_id in players_df.columns and c_id in db_df.columns:
        db_df[c_id] = db_df[c_id].astype(str).str.replace('"', '').str.replace("'", "").str.split('.').str[0].str.strip()
        players_df[p_id] = players_df[p_id].astype(str).str.replace('"', '').str.replace("'", "").str.split('.').str[0].str.strip()

        info_cols = [p_id, 'POS', 'ROLECODE3']
        spiller_info = players_df[[c for c in info_cols if c in players_df.columns]].drop_duplicates(subset=[p_id])
        df = db_df.merge(spiller_info, left_on=c_id, right_on=p_id, how='left')
    else:
        df = db_df.copy()

    # KOLONNE IDENTIFIKATION
    c_dato = find_col(df, 'dato')
    c_navn = find_col(df, 'navn')
    c_klub = find_col(df, 'klub')
    c_pos_visning = find_col(df, 'position')
    c_rating = find_col(df, 'rating_avg')
    c_status = find_col(df, 'status')
    c_scout = find_col(df, 'scout')

    # DATA FORMATERING
    df['DATO_DT'] = pd.to_datetime(df[c_dato], errors='coerce')
    df[c_rating] = pd.to_numeric(df[c_rating].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    # POSITION MAPPING
    df[c_pos_visning] = df.apply(map_position, axis=1)
    df = df.sort_values('DATO_DT')

    # UI & FILTER
    st.subheader("Scouting Database")
    
    valgt_status = st.session_state.get("filter_status", [])
    valgt_pos = st.session_state.get("filter_pos", [])
    rating_range = st.session_state.get("filter_rating", (0.0, 5.0))
    
    antal_filtre = len(valgt_status) + len(valgt_pos)
    if rating_range != (0.0, 5.0): antal_filtre += 1
    filter_label = f"Filtrér ({antal_filtre})" if antal_filtre > 0 else "Filtrér"

    col_s, col_p = st.columns([4, 1.2]) 
    with col_s:
        search = st.text_input("Søg...", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
    
    with col_p:
        with st.popover(filter_label, use_container_width=True):
            s_opts = sorted([str(x) for x in df[c_status].dropna().unique() if str(x).strip() != ""])
            valgt_status = st.multiselect("Status", options=s_opts, key="filter_status")
            p_opts = sorted([str(x) for x in df[c_pos_visning].unique() if str(x).strip() != ""])
            valgt_pos = st.multiselect("Position", options=p_opts, key="filter_pos")
            st.divider()
            rating_range = st.slider("Rating Interval", 0.0, 5.0, (0.0, 5.0), step=0.1, key="filter_rating")

    # FILTRERING
    f_df = df.groupby(c_id).tail(1).copy()
    if search:
        mask = f_df[c_navn].str.contains(search, case=False, na=False) | f_df[c_klub].str.contains(search, case=False, na=False)
        f_df = f_df[mask]
    if valgt_status:
        f_df = f_df[f_df[c_status].astype(str).isin(valgt_status)]
    if valgt_pos:
        f_df = f_df[f_df[c_pos_visning].isin(valgt_pos)]
    f_df = f_df[(f_df[c_rating] >= rating_range[0]) & (f_df[c_rating] <= rating_range[1])]

    # HOVEDTABEL
    vis_cols = [c_navn, c_pos_visning, c_klub, c_rating, c_status, c_dato, c_scout]
    event = st.dataframe(
        f_df[vis_cols],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        height=800, 
        column_config={
            c_rating: st.column_config.NumberColumn("Rating", format="%.1f"),
            c_pos_visning: "Position",
            c_dato: st.column_config.DateColumn("Dato", format="DD/MM/YYYY")
        }
    )

    # VIS DIALOG VED VALG
    if len(event.selection.rows) > 0:
        idx = event.selection.rows[0]
        p_row = f_df.iloc[idx]
        vis_profil({
            'ID': p_row[c_id], 'NAVN': p_row[c_navn], 'KLUB': p_row[c_klub], 
            'POSITION': p_row[c_pos_visning], 'RATING_AVG': p_row[c_rating]
        }, df, stats_df)
