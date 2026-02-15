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

# --- 2. PROFIL DIALOG ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df):
    clean_p_id = str(p_data['PLAYER_WYID']).split('.')[0].strip()
    historik = full_df[full_df['PLAYER_WYID'].astype(str) == clean_p_id].sort_values('DATO', ascending=True)
    
    if historik.empty:
        st.error("Data ikke fundet.")
        return

    nyeste = historik.iloc[-1]
    seneste_dato = hent_vaerdi_robust(nyeste, 'Dato')
    scout_navn = hent_vaerdi_robust(nyeste, 'Scout')

    head_col1, head_col2 = st.columns([1, 4])
    with head_col1:
        vis_spiller_billede(clean_p_id, w=115)
    with head_col2:
        st.markdown(f"<h2 style='margin-top:0;'>{p_data.get('NAVN', 'Ukendt')}</h2>", unsafe_allow_html=True)
        st.markdown(f"**{p_data.get('KLUB', '')}** | {p_data.get('POSITION', '')} | Snit: {p_data.get('RATING_AVG', 0)}")
        st.caption(f"Seneste rapport: {seneste_dato} | Scout: {scout_navn}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radarchart"])
    
    with tab1:
        m_cols = st.columns(4)
        metrics = [
            ("Beslutsomhed", "BESLUTSOMHED"), ("Fart", "FART"), 
            ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
            ("Udholdenhed", "UDHOLDENHED"), ("Lederegenskaber", "LEDEREGENSKABER"), 
            ("Teknik", "TEKNIK"), ("Spilintelligens", "SPILINTELLIGENS")
        ]
        for i, (label, col) in enumerate(metrics):
            val = rens_metrik_vaerdi(nyeste.get(col, 0))
            m_cols[i % 4].metric(label, f"{val}")
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', 'Ingen data')}")
        with c2: st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', 'Ingen data')}")
        with c3: st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', 'Ingen data')}")

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            with st.expander(f"Rapport: {row.get('DATO')} | Scout: {row.get('SCOUT')} | Rating: {row.get('RATING_AVG')}"):
                st.write(f"**Vurdering:** {row.get('VURDERING')}")

    with tab3:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO'], y=historik['RATING_AVG'], mode='markers+lines', line_color='#df003b'))
        fig_line.update_layout(height=450, yaxis=dict(range=[1, 6]), title="Rating over tid")
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        display_stats = s_df[s_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
        if not display_stats.empty:
            st.dataframe(display_stats, use_container_width=True, hide_index=True)
        else:
            st.info("Ingen statistisk data fundet for denne spiller.")

    with tab5:
        cl, cm, cr = st.columns([1.5, 4, 2.5])
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        cat_cols = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        v = [rens_metrik_vaerdi(nyeste.get(c, 0)) for c in cat_cols]
        v_closed = v + [v[0]]
        
        with cl:
            st.markdown(f"*{seneste_dato}*")
            for cat, val in zip(categories, v):
                st.markdown(f"**{cat}:** `{val}`")
        with cm:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=v_closed, theta=categories + [categories[0]], fill='toself', line_color='#df003b'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False)
            st.plotly_chart(fig_radar, use_container_width=True)
        with cr:
            st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
            st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    _, _, _, spillere_df, stats_df, scout_df = st.session_state["main_data"]

    # --- ULTRA-RENS AF ID'ER ---
    scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    # Merge data
    s_info = spillere_df[['PLAYER_WYID', 'POS', 'ROLECODE3']].drop_duplicates('PLAYER_WYID')
    df = scout_df.merge(s_info, on='PLAYER_WYID', how='left')
    
    # Map positioner og datoer
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    df = df.sort_values('DATO_DT')

    # UI & FILTRE
    st.subheader("Scouting Database")
    
    col_s, col_p = st.columns([4, 1.2])
    with col_s:
        search = st.text_input("Søg...", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
    
    with col_p:
        with st.popover("Filtrér", use_container_width=True):
            valgt_status = st.multiselect("Status", options=sorted(df['STATUS'].dropna().unique()))
            valgt_pos = st.multiselect("Position", options=sorted(df['POSITION_VISNING'].unique()))
            rating_range = st.slider("Rating", 0.0, 5.0, (0.0, 5.0), 0.1)

    # Filtrering til visning
    f_df = df.groupby('PLAYER_WYID').tail(1).copy()
    
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]
    if valgt_status:
        f_df = f_df[f_df['STATUS'].isin(valgt_status)]
    if valgt_pos:
        f_df = f_df[f_df['POSITION_VISNING'].isin(valgt_pos)]
    f_df = f_df[(f_df['RATING_AVG'] >= rating_range[0]) & (f_df['RATING_AVG'] <= rating_range[1])]

    # VISNING AF TABEL
    vis_cols = ['NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'DATO', 'SCOUT']
    event = st.dataframe(
        f_df[vis_cols],
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        height=700,
        column_config={
            "RATING_AVG": st.column_config.NumberColumn("Rating", format="%.1f"),
            "POSITION_VISNING": "Position"
        }
    )

    # HÅNDTER VALG
    if len(event.selection.rows) > 0:
        idx = event.selection.rows[0]
        p_row = f_df.iloc[idx]
        vis_profil({
            'PLAYER_WYID': p_row['PLAYER_WYID'], 'NAVN': p_row['NAVN'], 'KLUB': p_row['KLUB'], 
            'POSITION': p_row['POSITION_VISNING'], 'RATING_AVG': p_row['RATING_AVG']
        }, df, stats_df)

    # DEBUG MODUL
    with st.expander("🛠️ Debug: ID-Match Kontrol"):
        mangler = f_df[f_df['POS'].isna() & f_df['ROLECODE3'].isna()]
        if not mangler.empty:
            st.warning(f"Der er {len(mangler)} spillere, der ikke findes i players.csv")
            st.dataframe(mangler[['PLAYER_WYID', 'NAVN', 'KLUB']])
        else:
            st.success("Alle spillere matchet korrekt.")
