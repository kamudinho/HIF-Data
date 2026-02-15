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
        ("Tekniske færdigheder", "TEKNIK"), ("Fart", "FART"), 
        ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
        ("Udholdenhed", "UDHOLDENHED"), ("Lederegenskaber", "LEDEREGENSKABER"), 
        ("Beslutsomhed", "BESLUTSOMHED"), ("Spilintelligens", "SPILINTELLIGENS")
    ]
    for i, (label, col) in enumerate(metrics):
        val = rens_metrik_vaerdi(row.get(col, 0))
        m_cols[i % 4].metric(label, f"{val}")

# --- 3. PROFIL DIALOG ---
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
        with c1: st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
        with c2: st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")
        with c3: st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', '-')}")

    with tab2:
        for _, row in historik.iloc[::-1].iterrows():
            with st.expander(f"Rapport: {row.get('DATO')} | Scout: {row.get('SCOUT')} | Rating: {row.get('RATING_AVG')}"):
                vis_metrikker(row)
                st.divider()
                hc1, hc2, hc3 = st.columns(3)
                with hc1: st.success(f"**Styrker**\n\n{row.get('STYRKER', '-')}")
                with hc2: st.warning(f"**Udvikling**\n\n{row.get('UDVIKLING', '-')}")
                with hc3: st.info(f"**Vurdering**\n\n{row.get('VURDERING', '-')}")

    with tab3:
        h_col1, h_col2 = st.columns([2, 1])
        with h_col1:
            st.markdown("#### Udviklingskurve (1-6)")
        with h_col2:
            metrics_map = {
                "Gennemsnit": "RATING_AVG",
                "Beslutsomhed": "BESLUTSOMHED", "Fart": "FART",
                "Aggresivitet": "AGGRESIVITET", "Attitude": "ATTITUDE",
                "Udholdenhed": "UDHOLDENHED", "Lederegenskaber": "LEDEREGENSKABER",
                "Teknik": "TEKNIK", "Spilintelligens": "SPILINTELLIGENS"
            }
            valgt_label = st.selectbox("Parameter", options=list(metrics_map.keys()), index=0, label_visibility="collapsed")
            valgt_col = metrics_map[valgt_label]

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik[valgt_col], mode='markers+lines', line=dict(color='#df003b', width=2), marker=dict(size=8)))
        fig_line.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0.8, 6.2], tickvals=[1, 2, 3, 4, 5, 6]), plot_bgcolor='white', hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})

    with tab4:
        st.markdown("### 📊 Statistisk Historik")
        curr = s_df[s_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
        old = fs_df[fs_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
        df_stats = pd.concat([curr, old], ignore_index=True)

        if not df_stats.empty:
            display_stats = pd.DataFrame()
            if 'SEASONNAME' in df_stats.columns: display_stats['Sæson'] = df_stats['SEASONNAME']
            if 'TEAMNAME' in df_stats.columns: display_stats['Hold'] = df_stats['TEAMNAME']
            display_stats['Kampe'] = df_stats['MATCHES'].fillna(0).astype(int)
            display_stats['Minutter'] = df_stats['MINUTESTAGGED'].fillna(0).astype(int)
            display_stats['Mål'] = df_stats['GOALS'].fillna(0).astype(int)
            display_stats['Assists'] = df_stats['ASSISTS'].fillna(0).astype(int)
            
            # Her er rettelsen til kort-fejlen
            display_stats['Gule'] = df_stats['YELLOWCARD'].fillna(0).astype(int)
            display_stats['Røde'] = df_stats['REDCARDS'].fillna(0).astype(int)

            stat_map = {
                'Passes': ('PASSES', 'SUCCESSFULPASSES'),
                'Forward Passes': ('FORWARDPASSES', 'SUCCESSFULFORWARDPASSES'),
                'Final Third Passes': ('PASSESTOFINALTHIRD', 'SUCCESSFULPASSESTOFINALTHIRD'),
                'Progressive Passes': ('PROGRESSIVEPASSES', 'SUCCESSFULPROGRESSIVEPASSES'),
                'Duels': ('DUELS', 'DUELSWON')
            }
            for label, (total_col, success_col) in stat_map.items():
                if total_col in df_stats.columns and success_col in df_stats.columns:
                    display_stats[label] = df_stats.apply(lambda r: f"{int(r[total_col])} ({int((r[success_col]/r[total_col])*100)}%)" if r[total_col] > 0 else f"{int(r[total_col])} (0%)", axis=1)

            st.dataframe(display_stats.sort_values('Sæson', ascending=False) if 'Sæson' in display_stats.columns else display_stats, use_container_width=True, hide_index=True)
        else:
            st.info("Ingen statistisk data fundet.")

    with tab5:
        categories = ['Tekniske færdigheder', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Beslutsomhed', 'Spilintelligens']
        cols = ['TEKNIK', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'BESLUTSOMHED', 'SPILINTELLIGENS']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        
        cl, cm, cr = st.columns([1.5, 4, 2.5])
        with cl:
            st.markdown("### Detaljer")
            st.caption(f"**Dato:** {nyeste.get('DATO', '-')}\n\n**Scout:** {nyeste.get('SCOUT', '-')}")
            st.divider()
            for cat, val in zip(categories, v):
                st.markdown(f"**{cat}:** `{val}`")
        with cm:
            fig_radar = go.Figure(go.Scatterpolar(r=v+[v[0]], theta=categories+[categories[0]], fill='toself', line=dict(color='#df003b', width=2), fillcolor='rgba(223, 0, 59, 0.3)'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6], tickvals=[1,2,3,4,5,6], gridcolor="grey"), gridshape='linear'), showlegend=False, height=450)
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
    
    _, _, _, spillere_df, stats_df, scout_df, former_stats = st.session_state["main_data"]

    scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    spillere_df['PLAYER_WYID'] = spillere_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    df = scout_df.merge(spillere_df[['PLAYER_WYID', 'POS', 'ROLECODE3']].drop_duplicates('PLAYER_WYID'), on='PLAYER_WYID', how='left')
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    df = df.sort_values('DATO_DT')

    st.subheader("Scouting Database")
    search = st.text_input("Søg...", placeholder="Navn eller klub...", label_visibility="collapsed")
    
    f_df = df.groupby('PLAYER_WYID').tail(1).copy()
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]
    
    display_df = f_df[['NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'DATO', 'SCOUT']].copy()
    display_df.columns = ['NAVN', 'POSITION', 'KLUB', 'RATING', 'VURDERING', 'DATO', 'SCOUT']

    event = st.dataframe(display_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", height=600)

    if len(event.selection.rows) > 0:
        p_row = f_df.iloc[event.selection.rows[0]]
        vis_profil(p_row, df, stats_df, former_stats)
