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
        # 1. Saml data
        curr = s_df[s_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
        old = fs_df[fs_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
        df_stats = pd.concat([curr, old], ignore_index=True)

        if not df_stats.empty:
            # 2. Definer hvilke stats der skal have en %-beregning
            # Format: 'Visningsnavn': ('Total_kolonne', 'Succes_kolonne')
            stat_map = {
                'Passes': ('PASSES', 'SUCCESSFULPASSES'),
                'Forward Passes': ('FORWARDPASSES', 'SUCCESSFULFORWARDPASSES'),
                'Final Third Passes': ('PASSESTOFINALTHIRD', 'SUCCESSFULPASSESTOFINALTHIRD'),
                'Progressive Passes': ('PROGRESSIVEPASSES', 'SUCCESSFULPROGRESSIVEPASSES'),
                'Duels': ('DUELS', 'DUELSWON')
            }

            # 3. Lav en ny dataframe til visning
            display_stats = pd.DataFrame()
            
            # Tilføj basis-info først
            if 'SEASONNAME' in df_stats.columns: display_stats['Sæson'] = df_stats['SEASONNAME']
            if 'TEAMNAME' in df_stats.columns: display_stats['Hold'] = df_stats['TEAMNAME']
            display_stats['Kampe'] = df_stats['MATCHES']
            display_stats['Minutter'] = df_stats['MINUTESTAGGED']

            # 4. Beregn procenter og formater tekst: "Total (XX %)"
            for label, (total_col, success_col) in stat_map.items():
                if total_col in df_stats.columns and success_col in df_stats.columns:
                    def format_pct(row):
                        tot = row[total_col]
                        suc = row[success_col]
                        if tot > 0:
                            pct = (suc / tot) * 100
                            return f"{int(tot)} ({int(pct)}%)"
                        return f"{int(tot)} (0%)"
                    
                    display_stats[label] = df_stats.apply(format_pct, axis=1)

            # 5. Tilføj de resterende stats (mål, assists, etc.)
            andre_stats = {
                'GOALS': 'Mål',
                'ASSISTS': 'Assists',
                'TOUCHINBOX': 'Touch i felt',
                'YELLOWCARD': 'Gule',
                'REDCARDS': 'Røde'
            }
            
            for col, label in andre_stats.items():
                if col in df_stats.columns:
                    display_stats[label] = df_stats[col].fillna(0).astype(int)

            # Sorter efter nyeste sæson
            if 'Sæson' in display_stats.columns:
                display_stats = display_stats.sort_values('Sæson', ascending=False)

            # 6. Vis tabellen
            st.dataframe(display_stats, use_container_width=True, hide_index=True)
        else:
            st.info("Ingen statistisk data fundet.")

    with tab5:
        # 1. Forbered data
        categories = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        cols = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        
        # Hent værdier fra nyeste rapport
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        # Luk cirklen ved at tilføje første værdi til sidst
        v_closed = v + [v[0]]
        cat_closed = categories + [categories[0]]

        # 2. Layout: 3 kolonner
        cl, cm, cr = st.columns([1.5, 4, 2.5])

        with cl:
            st.markdown(f"### Detaljer")
            st.caption(f"**Dato:** {nyeste.get('DATO', '-')}")
            st.caption(f"**Scout:** {nyeste.get('SCOUT', '-')}")
            st.divider()
            # Vis værdier med farveindikation
            for cat, val in zip(categories, v):
                color = "#df003b" if val >= 4 else "#eee"
                st.markdown(f"**{cat}:** `{val}`")

        with cm:
            # Radar Chart med lineær grid (8-kant)
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=v_closed,
                theta=cat_closed,
                fill='toself',
                line=dict(color='#df003b', width=2),
                fillcolor='rgba(223, 0, 59, 0.3)',
                marker=dict(size=8, color='#df003b')
            ))

            fig_radar.update_layout(
                polar=dict(
                    angularaxis=dict(
                        tickfont=dict(size=11),
                        rotation=90,
                        direction="clockwise",
                        gridcolor="grey"
                    ),
                    radialaxis=dict(
                        visible=True,
                        range=[0, 6],
                        tickvals=[1, 2, 3, 4, 5, 6],
                        gridcolor="grey"
                    ),
                    gridshape='linear'  # DETTE GØR DEN TIL EN 8-KANT (IKKE CIRKEL)
                ),
                showlegend=False,
                height=450,
                margin=dict(l=40, r=40, t=20, b=20)
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with cr:
            st.markdown("### Bemærkninger")
            st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
            st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")
            st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', '-')}")

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
