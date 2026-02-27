import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from data.data_load import load_snowflake_query

# --- 1. HJÆLPEFUNKTIONER ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def map_position(row):
    role = str(row.get('ROLECODE3', '')).strip().upper()
    role_dict = {"GKP": "Målmand", "GK": "Målmand", "DEF": "Forsvarsspiller", "MID": "Midtbanespiller", "FWD": "Angriber"}
    if role in role_dict: return role_dict[role]
    csv_pos = str(row.get('POS', row.get('POSITION', 'Ukendt'))).strip().split('.')[0]
    pos_dict = {"1": "Målmand", "2": "Højre Back", "3": "Venstre Back", "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt", "7": "Højre Kant", "8": "Central Midt", "9": "Angriber", "10": "Offensiv Midt", "11": "Venstre Kant"}
    return pos_dict.get(csv_pos, role_dict.get(csv_pos.upper(), csv_pos))

def vis_spiller_billede(pid, w=110):
    pid_clean = str(pid).split('.')[0].strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except: st.image(std, width=w)

# --- 3. PROFIL DIALOG (Opdateret med korrekt indrykning og billede) ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df, career_df):
    try:
        raw_id = str(p_data['PLAYER_WYID']).split('.')[0].strip()
        clean_p_id = str(int(float(raw_id)))
    except:
        clean_p_id = str(p_data['PLAYER_WYID']).split('.')[0].strip()

    full_df['PLAYER_WYID'] = full_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error(f"Ingen rapporter fundet.")
        return
    
    nyeste = historik.iloc[-1]
    
    # Header sektion 🖼️
    img_url = p_data.get('IMAGEDATAURL')
    h1, h2 = st.columns([1, 4])
    
    with h1:
        # Her var fejlen – disse linjer er nu korrekt indrykket
        if pd.notna(img_url) and str(img_url).startswith("http"):
            st.image(img_url, width=115)
        else:
            vis_spiller_billede(clean_p_id, w=115)
            
    with h2:
        st.markdown(f"## {nyeste.get('NAVN', 'Ukendt')}")
        st.markdown(f"**{nyeste.get('KLUB', 'Ingen klub')}** | {nyeste.get('POSITION_VISNING', 'Ukendt')} | Snit: `{nyeste.get('RATING_AVG', 0)}`")
        
    t1, t2, t3, t4, t5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radar"])
    
    with t1:
        m_cols = st.columns(4)
        metrics = [("Teknik", "TEKNIK"), ("Fart", "FART"), ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
                   ("Udholdenhed", "UDHOLDENHED"), ("Leder", "LEDEREGENSKABER"), ("Beslutning", "BESLUTSOMHED"), ("Intelligens", "SPILINTELLIGENS")]
        for i, (label, col) in enumerate(metrics):
            m_cols[i % 4].metric(label, f"{rens_metrik_vaerdi(nyeste.get(col, 0))}")
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
        with c2: st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")
        with c3: st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', '-')}")

    with t2:
        for _, row in historik.iloc[::-1].iterrows():
            with st.expander(f"Dato: {row.get('DATO')} | Rating: {row.get('RATING_AVG')}"):
                st.write(row.get('VURDERING'))

    with t3:
        fig_line = go.Figure(go.Scatter(x=historik['DATO_DT'], y=historik['RATING_AVG'], mode='lines+markers', line=dict(color='#df003b')))
        fig_line.update_layout(yaxis=dict(range=[0, 6]), height=300)
        st.plotly_chart(fig_line, use_container_width=True)

    with t4:
        st.subheader("Karrierehistorik")
        if career_df is not None and not career_df.empty:
            career_df['PLAYER_WYID'] = career_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
            df_p = career_df[career_df['PLAYER_WYID'] == clean_p_id].copy()
            
            if not df_p.empty:
                df_p = df_p.sort_values('SEASONNAME', ascending=False)
                mapping = {
                    'SEASONNAME': 'Sæson', 'TEAMNAME': 'Klub', 'COMPETITIONNAME': 'Turnering',
                    'APPEARANCES': 'Kampe', 'MINUTESPLAYED': 'Min.', 'GOAL': 'Mål',
                    'YELLOWCARD': 'Gule', 'REDCARDS': 'Røde', 'SUBSTITUTEIN': 'Ind', 'SUBSTITUTEOUT': 'Ud'
                }
                vis_kolonner = [c for c in mapping.keys() if c in df_p.columns]
                st.dataframe(df_p[vis_kolonner].rename(columns=mapping), use_container_width=True, hide_index=True)
            else:
                st.info(f"Ingen karrieredata fundet i databasen for ID: {clean_p_id}")
        else:
            st.error("Kunne ikke få kontakt til karriere-tabellen i Snowflake.")

    with t5:
        st.subheader(f"Seneste rapport:")
        c_left, c_mid, c_right = st.columns([1, 2, 1.5])

        with c_left:
            st.markdown(f"""
            **Dato:** {nyeste.get('DATO', '-')}  
            **Scout:** {nyeste.get('SCOUT', '-')}
            """)
            
            metrics_list = [
                ("Beslutning", "BESLUTSOMHED"), ("Fart", "FART"), 
                ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
                ("Udholdenhed", "UDHOLDENHED"), ("Leder", "LEDEREGENSKABER"), 
                ("Teknik", "TEKNIK"), ("Intelligens", "SPILINTELLIGENS")
            ]
            for label, col in metrics_list:
                val = rens_metrik_vaerdi(nyeste.get(col, 0))
                st.markdown(f"**{label}:** `{val}`")

        with c_mid:
            categories = ['Beslutning', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Leder', 'Teknik', 'Intelligens']
            cols = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
            v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
            
            fig_radar = go.Figure(go.Scatterpolar(
                r=v + [v[0]], 
                theta=categories + [categories[0]], 
                fill='toself', 
                line=dict(color='#df003b', width=2),
                fillcolor='rgba(223, 0, 59, 0.3)',
                mode='lines+markers'
            ))
            
            fig_radar.update_layout(
                polar=dict(
                    gridshape='linear',
                    radialaxis=dict(visible=True, range=[0, 6], tickfont=dict(size=8)),
                    angularaxis=dict(rotation=90, direction="clockwise")
                ),
                showlegend=False,
                height=400,
                margin=dict(l=50, r=50, t=40, b=40)
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with c_right:
            st.markdown("### Vurdering")
            st.info(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
            st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")
            st.success(f"**Samlet**\n\n{nyeste.get('VURDERING', '-')}")
            
# --- 4. HOVEDFUNKTION ---
def vis_side(scout_df, spillere_df, stats_df, career_df):
    st.markdown('<div class="custom-header"><h3>Scouting-database</h3></div>', unsafe_allow_html=True)
    
    if "player_career_data" not in st.session_state or st.session_state["player_career_data"] is None:
        with st.spinner("Henter historik..."):
            df_career = load_snowflake_query("player_career", "('dummy')", "LIKE '%%'")
            if df_career is not None:
                df_career.columns = [c.upper() for c in df_career.columns]
                st.session_state["player_career_data"] = df_career
                st.rerun()

    career_df = st.session_state.get("player_career_data", pd.DataFrame())

    def clean_df(df):
        if df is not None and not df.empty and 'PLAYER_WYID' in df.columns:
            df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        return df

    scout_df = clean_df(scout_df)
    spillere_df = clean_df(spillere_df)
    career_df = clean_df(career_df)

    df = scout_df.copy()
    if spillere_df is not None and not spillere_df.empty:
        # Sørg for at få billed-URL med over i din filtrerede dataframe
        df = df.merge(spillere_df[['PLAYER_WYID', 'POS', 'ROLECODE3']].drop_duplicates('PLAYER_WYID'), on='PLAYER_WYID', how='left')
    
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    f_df = df.sort_values('DATO_DT').groupby('PLAYER_WYID').tail(1).copy()
    
    search = st.text_input("Søg...", placeholder="Navn, klub...")
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]

    std_placeholder = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    # 2. Forbered data til visning og håndter manglende billeder
    f_df['IMAGEDATAURL'] = f_df['IMAGEDATAURL'].fillna(std_placeholder)
    f_df.loc[f_df['IMAGEDATAURL'].str.strip() == "", 'IMAGEDATAURL'] = std_placeholder

    # 3. Vælg kolonner (Vi kalder billed-kolonnen 'Foto' her for at matche config)
    disp = f_df[['IMAGEDATAURL', 'NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS']].copy()
    disp.columns = [' ', 'Navn', 'Position', 'Klub', 'Rating', 'Status']
    
    tabel_hoejde = (len(f_df) + 1) * 35 + 10 
    
    # 4. Vis tabellen
    event = st.dataframe(
        disp, 
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        column_config={
            # Nøglen her SKAL matche navnet i disp.columns ('Foto')
            " ": st.column_config.ImageColumn(" ", width="small"), 
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f")
        },
        height=tabel_hoejde
    )
    if len(event.selection.rows) > 0:
        vis_profil(f_df.iloc[event.selection.rows[0]], df, stats_df, career_df)
