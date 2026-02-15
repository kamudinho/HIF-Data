import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests

# --- 1. HJÆLPEFUNKTIONER (Oversættelse & Rens) ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def map_position(row):
    """Præcis mapping baseret på de koder vi ser i dine data."""
    # Hovedfilen tvinger kolonnenavne til UPPERCASE
    db_text = str(row.get('POSITION', '')).strip()
    pos_raw = str(row.get('POS', '')).strip().split('.')[0]
    role_raw = str(row.get('ROLECODE3', '')).strip().upper()
    
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    
    role_map = {"GKP": "Målmand", "DEF": "Forsvarsspiller", "MID": "Midtbane", "FWD": "Angriber"}

    # Prioriteter
    if pos_raw in pos_dict: return pos_dict[pos_raw]
    db_pos_digit = db_text.split('.')[0]
    if db_pos_digit in pos_dict: return pos_dict[db_pos_digit]
    if len(db_text) > 2 and db_text.upper() not in ["NAN", "NONE", "UKENDT"] + list(role_map.keys()):
        return db_text
    return role_map.get(role_raw, "Ukendt")

def vis_spiller_billede(pid, w=110):
    pid_clean = str(pid).split('.')[0].strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except:
        st.image(std, width=w)

# --- 2. PROFIL DIALOG (MED ALT UDSTYR) ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df):
    clean_p_id = str(p_data['ID']).split('.')[0].strip()
    historik = full_df[full_df['ID'].astype(str) == clean_p_id].sort_values('DATO', ascending=True)
    
    if historik.empty:
        st.error("Data ikke fundet.")
        return

    nyeste = historik.iloc[-1]
    
    # Header
    h1, h2 = st.columns([1, 4])
    with h1: vis_spiller_billede(clean_p_id, w=115)
    with h2:
        st.markdown(f"<h2 style='margin-top:0;'>{p_data['NAVN']}</h2>", unsafe_allow_html=True)
        st.markdown(f"**{p_data['KLUB']}** | {p_data['POSITION']} | Snit: {p_data['RATING_AVG']}")
        st.caption(f"Seneste rapport: {nyeste.get('DATO','-')} | Scout: {nyeste.get('SCOUT','-')}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radarchart"])
    
    with tab1:
        m_cols = st.columns(4)
        cats = ["BESLUTSOMHED", "FART", "AGGRESIVITET", "ATTITUDE", "UDHOLDENHED", "LEDEREGENSKABER", "TEKNIK", "SPILINTELLIGENS"]
        for i, cat in enumerate(cats):
            val = rens_metrik_vaerdi(nyeste.get(cat, 0))
            m_cols[i%4].metric(cat.capitalize(), val)
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.success(f"**Styrker**\n\n{nyeste.get('STYRKER','-')}")
        c2.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING','-')}")
        c3.info(f"**Vurdering**\n\n{nyeste.get('VURDERING','-')}")

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            with st.expander(f"Rapport: {row.get('DATO','-')} | Scout: {row.get('SCOUT','-')} | Rating: {row.get('RATING_AVG',0)}"):
                st.write(f"**Vurdering:** {row.get('VURDERING','-')}")

    with tab3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=historik['DATO'], y=historik['RATING_AVG'], mode='markers+lines', line_color='#df003b'))
        fig.update_layout(height=400, yaxis=dict(range=[1, 6]), title="Rating historik")
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        # Stats fra season_stats.csv
        p_stats = s_df[s_df['PLAYER_WYID'].astype(str) == clean_p_id]
        if not p_stats.empty:
            st.dataframe(p_stats, use_container_width=True, hide_index=True)
        else: st.info("Ingen stats fundet.")

    with tab5:
        cl, cm, cr = st.columns([1.5, 4, 2.5])
        v = [rens_metrik_vaerdi(nyeste.get(c, 0)) for c in cats]
        v_closed = v + [v[0]]
        with cm:
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=v_closed, theta=[c.capitalize() for c in cats] + [cats[0].capitalize()], fill='toself', line_color='#df003b'))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False)
            st.plotly_chart(fig_r, use_container_width=True)

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state: return
    _, _, _, spillere_df, stats_df, scout_df = st.session_state["main_data"]

    # Merge med spillerinfo for at få POS og ROLECODE3
    s_info = spillere_df[['PLAYER_WYID', 'POS', 'ROLECODE3']].drop_duplicates('PLAYER_WYID')
    df = scout_df.merge(s_info, left_on='ID', right_on='PLAYER_WYID', how='left')
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)

    # UI Filters
    st.subheader("Scouting Database")
    
    col_s, col_p = st.columns([4, 1.2])
    with col_s:
        search = st.text_input("Søg spiller...", label_visibility="collapsed")
    
    # Popover filter (som du havde det)
    with col_p:
        with st.popover("Filtrér", use_container_width=True):
            f_status = st.multiselect("Status", options=sorted(df['STATUS'].unique()))
            f_pos = st.multiselect("Position", options=sorted(df['POSITION_VISNING'].unique()))
            f_rating = st.slider("Rating", 0.0, 5.0, (0.0, 5.0), 0.1)

    # Filtrering af data
    f_df = df.groupby('ID').tail(1).copy()
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]
    if f_status: f_df = f_df[f_df['STATUS'].isin(f_status)]
    if f_pos: f_df = f_df[f_df['POSITION_VISNING'].isin(f_pos)]
    f_df = f_df[(f_df['RATING_AVG'] >= f_rating[0]) & (f_df['RATING_AVG'] <= f_rating[1])]

    # Tabel visning
    vis_cols = ['NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'DATO']
    event = st.dataframe(
        f_df[vis_cols],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "RATING_AVG": st.column_config.NumberColumn("Rating", format="%.1f"),
            "POSITION_VISNING": "Position"
        }
    )

    if len(event.selection.rows) > 0:
        idx = event.selection.rows[0]
        row = f_df.iloc[idx]
        vis_profil({
            'ID': row['ID'], 'NAVN': row['NAVN'], 'KLUB': row['KLUB'], 
            'POSITION': row['POSITION_VISNING'], 'RATING_AVG': row['RATING_AVG']
        }, df, stats_df)
