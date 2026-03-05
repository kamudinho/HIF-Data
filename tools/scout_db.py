import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

# --- HJÆLPEFUNKTIONER ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def map_position(row):
    # Tjek først dit eget 1-11 system (POS) fra players.csv
    pos_val = str(row.get('POS', '')).split('.')[0].strip()
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back", "4": "Midtstopper", 
        "5": "Midtstopper", "6": "Defensiv Midt", "7": "Højre Kant", "8": "Central Midt", 
        "9": "Angriber", "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    if pos_val in pos_dict: return pos_dict[pos_val]
    
    # Fallback til ROLECODE3 fra Wyscout hvis POS mangler
    role = str(row.get('ROLECODE3', '')).strip().upper()
    role_dict = {"GKP": "Målmand", "DEF": "Forsvar", "MID": "Midtbane", "FWD": "Angriber"}
    return role_dict.get(role, "Ukendt")

def vis_spiller_billede(pid, w=110):
    pid_clean = str(pid).split('.')[0].strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except: st.image(std, width=w)

@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, career_df):
    clean_p_id = str(p_data['PLAYER_WYID']).split('.')[0].strip()
    # Find historik for den specifikke spiller i scouting_db
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error("Ingen rapporter fundet.")
        return
    
    nyeste = historik.iloc[-1]
    
    # Header sektion med billede og stamdata
    h1, h2 = st.columns([1, 4])
    with h1:
        img_url = p_data.get('IMAGEDATAURL')
        if pd.notna(img_url) and str(img_url).startswith("http"):
            st.image(img_url, width=115)
        else:
            vis_spiller_billede(clean_p_id, w=115)
            
    with h2:
        st.markdown(f"## {nyeste.get('NAVN', 'Ukendt')}")
        st.markdown(f"**{nyeste.get('KLUB', 'Ingen klub')}** | {nyeste.get('POSITION_VISNING', 'Ukendt')} | Snit: `{nyeste.get('RATING_AVG', 0)}`")
        if pd.notna(p_data.get('CONTRACT')) and str(p_data.get('CONTRACT')).strip() != "":
            st.caption(f"Kontraktudløb: {p_data.get('CONTRACT')}")

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
        fig_line.update_layout(yaxis=dict(range=[0, 6]), height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_line, use_container_width=True)

    with t4:
        if career_df is not None and not career_df.empty:
            df_p = career_df[career_df['PLAYER_WYID'] == clean_p_id].copy()
            if not df_p.empty:
                mapping = {'SEASONNAME': 'Sæson', 'TEAMNAME': 'Klub', 'COMPETITIONNAME': 'Turnering', 'APPEARANCES': 'Kampe', 'GOAL': 'Mål'}
                st.dataframe(df_p[list(mapping.keys())].rename(columns=mapping), use_container_width=True, hide_index=True)
            else:
                st.info("Ingen karrieredata fundet i Snowflake.")

    with t5:
        categories = ['Beslutning', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Leder', 'Teknik', 'Intelligens']
        cols = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        fig_radar = go.Figure(go.Scatterpolar(r=v + [v[0]], theta=categories + [categories[0]], fill='toself', line=dict(color='#df003b')))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False)
        st.plotly_chart(fig_radar, use_container_width=True)

def vis_side(scout_df, players_local, sql_players, career_df):
    st.title("Scouting Database")
    
    # 1. FORBERED DATA - Rens ID'er kun hvis de findes
    for d in [scout_df, players_local, sql_players, career_df]:
        if d is not None and not d.empty and 'PLAYER_WYID' in d.columns:
            d['PLAYER_WYID'] = d['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
            
    # 2. HÅNDTER TOM SCOUT_DF (Fixer 'NoneType' fejlen)
    if scout_df is None or scout_df.empty:
        # Hvis vi ingen rapporter har, bruger vi de lokale spillere som base
        if players_local is not None and not players_local.empty:
            df = players_local.copy()
        else:
            st.warning("Ingen data fundet i hverken scouting_db eller players.csv")
            return
    else:
        df = scout_df.copy()
    
    # Byg lookup tabel: Start med lokale data (Contract/POS) og flet Wyscout billeder på
    if players_local is not None and not players_local.empty:
        lookup = players_local.copy()
        if sql_players is not None and not sql_players.empty:
            # Vi tager kun billederne fra SQL for at undgå kolonne-clash
            sql_img = sql_players[['PLAYER_WYID', 'IMAGEDATAURL']].drop_duplicates('PLAYER_WYID')
            lookup = lookup.merge(sql_img, on='PLAYER_WYID', how='left')
    else:
        lookup = sql_players if sql_players is not None else pd.DataFrame()

    # Flet stamdata ind på scouting rapporterne
    if not lookup.empty:
        # suffixes sikrer at vi ikke får dubletter hvis NAVN findes begge steder
        df = df.merge(lookup.drop_duplicates('PLAYER_WYID'), on='PLAYER_WYID', how='left', suffixes=('', '_extra'))

    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    
    # Tag kun den seneste rapport pr. spiller til oversigten
    f_df = df.sort_values('DATO_DT').groupby('PLAYER_WYID').tail(1).copy()
    
    search = st.text_input("Søg i databasen...", placeholder="Navn eller klub...")
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]

    # 3. TABELVISNING
    vis_cols = ['NAVN', 'POSITION_VISNING', 'POS', 'KLUB', 'RATING_AVG', 'CONTRACT', 'STATUS']
    if 'IMAGEDATAURL' in f_df.columns:
        vis_cols.insert(0, 'IMAGEDATAURL')
        
    disp = f_df[vis_cols].copy()
    col_map = {
        'IMAGEDATAURL': ' ', 
        'NAVN': 'Navn', 
        'POSITION_VISNING': 'Type', 
        'POS': 'Nr', 
        'KLUB': 'Klub', 
        'RATING_AVG': 'Rating', 
        'CONTRACT': 'Kontrakt', 
        'STATUS': 'Status'
    }
    disp = disp.rename(columns=col_map)
    
    event = st.dataframe(
        disp, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
        column_config={
            " ": st.column_config.ImageColumn(" ", width="small"),
            "Rating": st.column_config.NumberColumn(format="%.1f")
        }
    )
    
    if len(event.selection.rows) > 0:
        # Vis dialog med fuld profil for den valgte spiller
        vis_profil(f_df.iloc[event.selection.rows[0]], df, career_df)
