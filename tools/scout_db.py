import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from io import StringIO
from data.data_load import load_snowflake_query

# --- 1. HJÆLPEFUNKTIONER ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def map_position(row):
    role = str(row.get('ROLECODE3', '')).strip().upper()
    role_dict = {
        "GKP": "Målmand", "GK": "Målmand",
        "DEF": "Forsvarsspiller",
        "MID": "Midtbanespiller",
        "FWD": "Angriber"
    }
    if role in role_dict: return role_dict[role]

    csv_pos = str(row.get('POS', row.get('POSITION', 'Ukendt'))).strip().split('.')[0]
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    return pos_dict.get(csv_pos, role_dict.get(csv_pos.upper(), csv_pos))

def vis_spiller_billede(pid, w=110):
    pid_clean = str(pid).split('.')[0].strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except: st.image(std, width=w)

def vis_metrikker(row):
    m_cols = st.columns(4)
    metrics = [
        ("Teknik", "TEKNIK"), ("Fart", "FART"), 
        ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
        ("Udholdenhed", "UDHOLDENHED"), ("Leder", "LEDEREGENSKABER"), 
        ("Beslutning", "BESLUTSOMHED"), ("Intelligens", "SPILINTELLIGENS")
    ]
    for i, (label, col) in enumerate(metrics):
        val = rens_metrik_vaerdi(row.get(col, 0))
        m_cols[i % 4].metric(label, f"{val}")

# --- 2. PROFIL DIALOG ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df, career_df):
    clean_p_id = str(p_data['PLAYER_WYID']).split('.')[0].strip()
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error("Ingen historiske data fundet.")
        return
        
    nyeste = historik.iloc[-1]
    
    head_col1, head_col2 = st.columns([1, 4])
    with head_col1: vis_spiller_billede(clean_p_id, w=115)
    with head_col2:
        st.markdown(f"## {nyeste.get('NAVN', 'Ukendt')}")
        st.markdown(f"**{nyeste.get('KLUB', '')}** | {nyeste.get('POSITION_VISNING', '')} | Snit: `{nyeste.get('RATING_AVG', 0)}`")

    t1, t2, t3, t4, t5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radar"])
    
    with t1:
        vis_metrikker(nyeste)
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
        with c2: st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")
        with c3: st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', '-')}")

    with t2:
        for _, row in historik.iloc[::-1].iterrows():
            with st.expander(f"Dato: {row.get('DATO')} | Scout: {row.get('SCOUT')} | Rating: {row.get('RATING_AVG')}"):
                vis_metrikker(row)
                st.info(f"**Vurdering:** {row.get('VURDERING', '-')}")

    with t3:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik['RATING_AVG'], mode='markers+lines', line=dict(color='#df003b', width=3)))
        fig_line.update_layout(title="Rating udvikling", height=300, yaxis=dict(range=[0.8, 6.2]), plot_bgcolor='white')
        st.plotly_chart(fig_line, use_container_width=True)

    with t4:
        # --- A: SÆSON STATS (Fra Snowflake stats_df) ---
        st.markdown("### 📊 Sæsonstatistik (Aktuel)")
        if s_df is not None and not s_df.empty:
            p_stats = s_df[s_df['PLAYER_WYID'].astype(str) == clean_p_id]
            if not p_stats.empty:
                row = p_stats.iloc[0]
                s1, s2, s3, s4 = st.columns(4)
                
                def s_val(col, is_float=False):
                    v = row.get(col, 0)
                    return float(v) if is_float else int(v)

                s1.metric("Kampe", s_val('MATCHES'))
                s1.metric("Minutter", f"{s_val('MINUTESONFIELD')} '")
                s2.metric("Mål", s_val('GOALS'))
                s2.metric("Assists", s_val('ASSISTS'))
                s3.metric("xG", round(s_val('XGSHOT', True), 2))
                s3.metric("Afslutninger", s_val('SHOTS'))
                s4.metric("Driblinger", s_val('DRIBBLES'))
                s4.metric("Interceptions", s_val('INTERCEPTIONS'))
                st.divider()
            else:
                st.info("Ingen aktive statistikker fundet for denne sæson.")

        # --- B: KARRIEREHISTORIK (Fra career_df) ---
        st.markdown("### 📜 Karrierehistorik")
        if career_df is not None and not career_df.empty:
            df_p = career_df[career_df['PLAYER_WYID'].astype(str) == clean_p_id].copy()
            if not df_p.empty:
                # Rensning af karrierevisning
                df_p = df_p.drop_duplicates().rename(columns={
                    'SEASONNAME': 'SÆSON', 'COMPETITIONNAME': 'TURNERING',
                    'TEAMNAME': 'HOLD', 'APPEARANCES': 'KAMPE',
                    'MINUTESPLAYED': 'MIN', 'GOAL': 'MÅL', 'ASSIST': 'ASS'
                })
                # Filter bort helt små ungdomsrækker hvis nødvendigt
                pattern = 'U15|U14|U13'
                df_p = df_p[~df_p['TURNERING'].str.contains(pattern, case=False, na=False)]
                
                vis_cols = ['SÆSON', 'TURNERING', 'HOLD', 'KAMPE', 'MIN', 'MÅL', 'ASS']
                existing_cols = [c for c in vis_cols if c in df_p.columns]
                
                st.dataframe(df_p[existing_cols].sort_values(['SÆSON'], ascending=False), 
                             use_container_width=True, hide_index=True)
            else:
                st.info("Ingen historiske karrierestatistikker fundet (U16+).")

    with t5:
        categories = ['Teknik', 'Spilintelligens', 'Beslutning', 'Leder', 'Udholdenhed', 'Fart', 'Aggresivitet', 'Attitude']
        cols = ['TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'LEDEREGENSKABER', 'UDHOLDENHED', 'FART', 'AGGRESIVITET', 'ATTITUDE']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        v_closed = v + [v[0]]
        cat_closed = categories + [categories[0]]

        col_left, col_mid, col_right = st.columns([1.5, 4, 2.5])
        with col_left:
            st.markdown("### Detaljer")
            for cat, val in zip(categories, v):
                st.markdown(f"**{cat}:** <span style='color:#df003b; font-weight:bold;'>{val}</span>", unsafe_allow_html=True)
        with col_mid:
            fig_radar = go.Figure(go.Scatterpolar(r=v_closed, theta=cat_closed, fill='toself', line=dict(color='#df003b', width=2), fillcolor='rgba(223, 0, 59, 0.3)'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=400)
            st.plotly_chart(fig_radar, use_container_width=True)
        with col_right:
            st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
            st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")

# --- 3. HOVEDFUNKTION ---
def vis_side(scout_df, spillere_df, stats_df, career_placeholder):
    st.markdown('<div class="custom-header"><h3>Scouting-database</h3></div>', unsafe_allow_html=True)

    # LAZY LOADING AF KARRIERE-DATA
    if "player_career_data" not in st.session_state:
        with st.spinner("Henter karrierehistorik..."):
            dp = st.session_state["data_package"]
            st.session_state["player_career_data"] = load_snowflake_query("player_career", dp["comp_filter"], dp["season_filter"])
            st.rerun()
    
    career_df = st.session_state["player_career_data"]

    # Uniformering af kolonner til UPPERCASE
    for d in [scout_df, spillere_df, stats_df, career_df]:
        if d is not None and not d.empty:
            d.columns = [c.upper() for c in d.columns]

    def clean_id(df):
        if df is not None and 'PLAYER_WYID' in df.columns:
            df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        return df

    scout_df = clean_id(scout_df)
    spillere_df = clean_id(spillere_df)
    stats_df = clean_id(stats_df)
    career_df = clean_id(career_df)

    if scout_df is None or scout_df.empty:
        st.warning("Databasen er tom.")
        return

    # Merge med spillere_df for at få positioner hvis muligt
    df = scout_df.copy()
    if spillere_df is not None and not spillere_df.empty:
        cols_to_use = [c for c in ['PLAYER_WYID', 'POS', 'ROLECODE3'] if c in spillere_df.columns]
        df = df.merge(spillere_df[cols_to_use].drop_duplicates('PLAYER_WYID'), on='PLAYER_WYID', how='left')
    
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    
    # Vis kun nyeste rapport i hovedoversigten
    f_df = df.sort_values('DATO_DT').groupby('PLAYER_WYID').tail(1).copy()
    
    search = st.text_input("Søg i databasen...", placeholder="Navn, klub eller position...")
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | 
                    f_df['KLUB'].str.contains(search, case=False, na=False) | 
                    f_df['POSITION_VISNING'].str.contains(search, case=False, na=False)]
    
    disp = f_df[['NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'DATO', 'SCOUT']].copy()
    disp.columns = ['NAVN', 'POSITION', 'KLUB', 'RATING', 'STATUS', 'DATO', 'SCOUT']
    
    h = min((len(disp) + 1) * 35 + 40, 500)
    event = st.dataframe(disp, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", height=h)

    if len(event.selection.rows) > 0:
        vis_profil(f_df.iloc[event.selection.rows[0]], df, stats_df, career_df)
