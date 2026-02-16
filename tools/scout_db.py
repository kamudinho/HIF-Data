import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. HJÆLPEFUNKTIONER ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def map_position(row):
    csv_pos = str(row.get('POS', row.get('POSITION', 'Ukendt'))).strip().split('.')[0]
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    return pos_dict.get(csv_pos, csv_pos)

def vis_spiller_billede(pid, w=110):
    pid_clean = str(pid).split('.')[0].strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except: st.image(std, width=w)

# --- 2. LAYOUT FUNKTIONER ---
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

# --- 3. PROFIL DIALOG ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df, fs_df):
    # 1. Sikr os at s_df og full_df har store bogstaver
    if s_df is not None and not s_df.empty:
        s_df.columns = [c.upper() for c in s_df.columns]
    
    # Vi tvinger også kolonnerne i den lokale historik-df til store bogstaver
    full_df.columns = [c.upper() for c in full_df.columns]
        
    clean_p_id = str(p_data['PLAYER_WYID']).split('.')[0].strip()
    
    # Hent alle historiske rapporter for denne spiller
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error("Ingen historiske data fundet.")
        return
        
    nyeste = historik.iloc[-1]
    
    head_col1, head_col2 = st.columns([1, 4])
    with head_col1: vis_spiller_billede(clean_p_id, w=115)
    with head_col2:
        st.markdown(f"## {nyeste.get('NAVN', 'Ukendt')}")
        # Bemærk: Vi bruger UPPERCASE her (POSITION_VISNING, RATING_AVG)
        st.markdown(f"**{nyeste.get('KLUB', '')}** | {nyeste.get('POSITION_VISNING', '')} | Snit: {nyeste.get('RATING_AVG', 0)}")

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
            # Vi bruger DATO, SCOUT, RATING_AVG i store bogstaver
            with st.expander(f"Dato: {row.get('DATO')} | Scout: {row.get('SCOUT')} | Rating: {row.get('RATING_AVG')}"):
                vis_metrikker(row)

    with t3:
        # FEJL-RETTELSE HER: Brug store bogstaver for DATO_DT og RATING_AVG
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=historik['DATO_DT'], 
            y=historik['RATING_AVG'], 
            mode='markers+lines', 
            line=dict(color='#df003b')
        ))
        fig_line.update_layout(
            height=300, 
            yaxis=dict(range=[0.8, 6.2], title="Rating"), 
            xaxis=dict(title="Dato"),
            plot_bgcolor='white'
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        st.markdown("### 📊 Statistisk Historik (Snowflake)")
        
        # Vi gør tjekket ekstremt bredt for at finde PLAYER_WYID
        target_col = None
        if s_df is not None and not s_df.empty:
            # Find kolonnen uanset om den hedder player_wyid, PLAYER_WYID eller Player_Wyid
            potential_cols = [c for c in s_df.columns if c.upper() == 'PLAYER_WYID']
            if potential_cols:
                target_col = potential_cols[0]

        if target_col:
            df_stats = s_df[s_df[target_col].astype(str) == clean_p_id].copy()
            if not df_stats.empty:
                # Sørg for store bogstaver til visning
                df_stats.columns = [c.upper() for c in df_stats.columns]
                cols_to_show = ['SEASONNAME', 'TEAMNAME', 'MATCHES', 'GOALS', 'XG', 'ASSISTS']
                existing_cols = [c for c in cols_to_show if c in df_stats.columns]
                st.dataframe(df_stats[existing_cols], use_container_width=True, hide_index=True)
            else:
                st.info(f"Ingen Snowflake-stats fundet for ID: {clean_p_id}")
        else:
            st.warning("Snowflake-data kunne ikke matches (PLAYER_WYID mangler).")

    with tab5:
        # DIT ORIGINALE RADAR DESIGN
        categories = ['Tekniske færdigheder', 'Spilintelligens', 'Beslutsomhed', 'Lederegenskaber', 
                      'Udholdenhed', 'Fart', 'Aggresivitet', 'Attitude']
        cols = ['TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'LEDEREGENSKABER', 
                'UDHOLDENHED', 'FART', 'AGGRESIVITET', 'ATTITUDE']
        
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        v_closed = v + [v[0]]
        cat_closed = categories + [categories[0]]

        col_left, col_mid, col_right = st.columns([1.5, 4, 2.5])
        
        with col_left:
            st.markdown("### Detaljer")
            for cat, val in zip(categories, v):
                st.markdown(f"**{cat}:** <span style='color:#df003b; font-weight:bold;'>{val}</span>", unsafe_allow_html=True)

        with col_mid:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=v_closed, theta=cat_closed, fill='toself',
                line=dict(color='#df003b', width=2),
                fillcolor='rgba(223, 0, 59, 0.3)',
                marker=dict(size=8, color='#df003b')
            ))
            fig_radar.update_layout(
                polar=dict(
                    angularaxis=dict(rotation=90, direction="clockwise", gridcolor="lightgrey"),
                    radialaxis=dict(visible=True, range=[0, 6], tickvals=[1, 2, 3, 4, 5, 6], gridcolor="lightgrey"),
                    gridshape='linear' # Dette giver 8-kanten
                ),
                showlegend=False, height=450, margin=dict(l=60, r=60, t=30, b=30)
            )
            st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})

        with col_right:
            st.markdown("### Bemærkninger")
            st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
            st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")
            st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', '-')}")

# --- 4. HOVEDFUNKTION ---
def vis_side(scout_df, spillere_df, stats_df):
    # Standardisering af kolonnenavne til UPPERCASE
    for d in [scout_df, spillere_df, stats_df]:
        if d is not None and not d.empty:
            d.columns = [c.upper() for c in d.columns]
    
    # ID Rensning (Sikrer at vi kan merge på tværs af kilder)
    def clean(df):
        if df is not None and not df.empty and 'PLAYER_WYID' in df.columns:
            df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        return df

    scout_df = clean(scout_df)
    spillere_df = clean(spillere_df)
    stats_df = clean(stats_df)

    # Merge scouting rapporter med metadata fra players.csv
    df = scout_df.copy()
    if spillere_df is not None and not spillere_df.empty:
        df = df.merge(
            spillere_df[['PLAYER_WYID', 'POS', 'ROLECODE3']].drop_duplicates('PLAYER_WYID'), 
            on='PLAYER_WYID', 
            how='left'
        )
    
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    
    st.subheader("Scouting Database")
    
    # Oversigtstabellen: Vis kun den nyeste rapport pr. spiller
    f_df = df.sort_values('DATO_DT').groupby('PLAYER_WYID').tail(1).copy()
    
    search = st.text_input("Søg...", placeholder="Navn eller klub...", label_visibility="collapsed")
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | 
                    f_df['KLUB'].str.contains(search, case=False, na=False)]
    
    disp = f_df[['NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'DATO', 'SCOUT']].copy()
    disp.columns = ['NAVN', 'POSITION', 'KLUB', 'RATING', 'VURDERING', 'DATO', 'SCOUT']
    
    event = st.dataframe(disp, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

    if len(event.selection.rows) > 0:
        p_row = f_df.iloc[event.selection.rows[0]]
        # Vi sender stats_df med ind i profil-dialogen
        vis_profil(p_row, df, stats_df, pd.DataFrame())
