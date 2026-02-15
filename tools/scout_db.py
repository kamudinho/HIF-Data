import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests

# --- 1. HJÆLPEFUNKTIONER ---
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
    db_pos = str(row.get('POSITION', '')).strip().split('.')[0]
    csv_pos = str(row.get('POS', '')).strip().split('.')[0]
    role_raw = str(row.get('ROLECODE3', '')).strip().upper()
    
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    
    role_map = {"GKP": "Målmand", "DEF": "Forsvarsspiller", "MID": "Midtbane", "FWD": "Angriber"}

    if csv_pos in pos_dict: return pos_dict[csv_pos]
    if db_pos in pos_dict: return pos_dict[db_pos]
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

# --- 2. LAYOUT FUNKTIONER ---
def vis_metrikker(row):
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

def vis_bokse_lodret(row):
    st.success(f"**Styrker**\n\n{row.get('STYRKER', '-')}")
    st.warning(f"**Udvikling**\n\n{row.get('UDVIKLING', '-')}")
    st.info(f"**Vurdering**\n\n{row.get('VURDERING', '-')}")

# --- 3. PROFIL DIALOG (Opdateret med historisk statistik) ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df, fs_df):
    clean_p_id = str(p_data['PLAYER_WYID']).split('.')[0].strip()
    historik = full_df[full_df['PLAYER_WYID'].astype(str) == clean_p_id].sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error("Data ikke fundet.")
        return

    nyeste = historik.iloc[-1]
    
    head_col1, head_col2 = st.columns([1, 4])
    with head_col1:
        vis_spiller_billede(clean_p_id, w=115)
    with head_col2:
        st.markdown(f"<h2 style='margin-top:0;'>{p_data.get('NAVN', 'Ukendt')}</h2>", unsafe_allow_html=True)
        st.markdown(f"**{p_data.get('KLUB', '')}** | {p_data.get('POSITION', '')} | Snit: {p_data.get('RATING_AVG', 0)}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radar"])
    
    with tab1:
        vis_metrikker(nyeste)
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', 'Ingen data')}")
        with c2: st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', 'Ingen data')}")
        with c3: st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', 'Ingen data')}")

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            with st.expander(f"Rapport: {row.get('DATO')} | Scout: {row.get('SCOUT')} | Rating: {row.get('RATING_AVG')}"):
                vis_metrikker(row)

    with tab3:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik['RATING_AVG'], mode='markers+lines', line_color='#df003b'))
        fig_line.update_layout(height=400, yaxis=dict(range=[1, 6], title="Rating"))
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        st.markdown("### Historik")
        
        # 1. Hent data fra begge kilder
        curr = s_df[s_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
        old = fs_df[fs_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
        
        # 2. Læg dem sammen til én tabel
        # Vi bruger pd.concat for at lægge rækkerne under hinanden
        samlet_stats = pd.concat([curr, old], ignore_index=True)

        if not samlet_stats.empty:
            # 3. Rensning: Fjern PLAYER_WYID og dubletter hvis de findes
            samlet_stats = samlet_stats.drop(columns=['PLAYER_WYID'], errors='ignore')
            
            # 4. Sortering: Hvis du har en SEASONNAME kolonne, bruger vi den. 
            # Ellers vises de bare i rækkefølgen: Nyeste (curr) først, derefter gamle (old).
            if 'SEASONNAME' in samlet_stats.columns:
                samlet_stats = samlet_stats.sort_values('SEASONNAME', ascending=False)
            
            # 5. Vis den samlede tabel
            st.dataframe(
                samlet_stats, 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Ingen statistisk data fundet for denne spiller.")

    with tab5:
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        cols = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=v + [v[0]], theta=categories + [categories[0]], fill='toself', line_color='#df003b'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, height=400)
        st.plotly_chart(fig_radar, use_container_width=True)

# --- 4. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    # Udpak alle 7 elementer (former_stats er nr. 6)
    _, _, _, spillere_df, stats_df, scout_df, former_stats = st.session_state["main_data"]

    # Rens ID'er
    scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    s_info = spillere_df[['PLAYER_WYID', 'POS', 'ROLECODE3']].drop_duplicates('PLAYER_WYID')
    df = scout_df.merge(s_info, on='PLAYER_WYID', how='left')
    
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    df = df.sort_values('DATO_DT')

    st.subheader("Scouting Database")
    
    # Simple Filtre
    col_s, col_p = st.columns([4, 1.2])
    with col_s:
        search = st.text_input("Søg...", placeholder="Navn eller klub...", label_visibility="collapsed")
    with col_p:
        with st.popover("Filtrér", use_container_width=True):
            valgt_status = st.multiselect("Status", options=sorted(df['STATUS'].dropna().unique()))
            rating_range = st.slider("Rating", 0.0, 5.0, (0.0, 5.0), 0.1)

    f_df = df.groupby('PLAYER_WYID').tail(1).copy()
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]
    if valgt_status: f_df = f_df[f_df['STATUS'].isin(valgt_status)]
    f_df = f_df[(f_df['RATING_AVG'] >= rating_range[0]) & (f_df['RATING_AVG'] <= rating_range[1])]

    display_df = f_df[['NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'DATO', 'SCOUT']].copy()
    display_df.columns = ['NAVN', 'POSITION', 'KLUB', 'RATING', 'VURDERING', 'DATO', 'SCOUT']

    event = st.dataframe(
        display_df, 
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row", 
        height=600
    )

    if len(event.selection.rows) > 0:
        idx = event.selection.rows[0]
        p_row = f_df.iloc[idx]
        vis_profil({
            'PLAYER_WYID': p_row['PLAYER_WYID'], 'NAVN': p_row['NAVN'], 'KLUB': p_row['KLUB'], 
            'POSITION': p_row['POSITION_VISNING'], 'RATING_AVG': p_row['RATING_AVG']
        }, df, stats_df, former_stats)
