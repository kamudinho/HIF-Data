import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

def rens_id(val):
    """Sikrer at ID altid er en ren streng uden .0"""
    if pd.isna(val): return ""
    return str(val).split('.')[0].strip()

def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def map_position(row):
    pos_val = rens_id(row.get('POS', ''))
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back", "4": "Midtstopper", 
        "5": "Midtstopper", "6": "Defensiv Midt", "7": "Højre Kant", "8": "Central Midt", 
        "9": "Angriber", "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    if pos_val in pos_dict: return pos_dict[pos_val]
    return str(row.get('POSITION', 'Ukendt'))

def vis_spiller_billede(pid, w=110):
    pid_clean = rens_id(pid)
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except: st.image(std, width=w)

@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, career_df):
    clean_p_id = rens_id(p_data['PLAYER_WYID'])
    
    # Hent historikken for spilleren
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].copy()
    if 'DATO_DT' in historik.columns:
        historik = historik.sort_values('DATO_DT', ascending=True)
    
    nyeste = historik.iloc[-1]
    
    h1, h2 = st.columns([1, 4])
    with h1:
        # VI BRUGER DEN URL VI FANDT I OVERSIGTEN (som vi ved virker)
        img_url = p_data.get('VIS_BILLEDE')
        
        # Hvis den mod forventning er tom, tjekker vi om der er en direkte URL i data
        if not img_url:
            img_url = p_data.get('IMAGEDATAURL')

        if pd.notna(img_url) and str(img_url).startswith("http"):
            st.image(img_url, width=115)
        else:
            # Den grå silhuet hvis ALT fejler
            st.image("https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png", width=115)
            
    with h2:
        st.markdown(f"## {nyeste.get('NAVN', 'Ukendt')}")
        st.markdown(f"**{nyeste.get('KLUB', 'Ingen klub')}** | {nyeste.get('POSITION_VISNING', 'Ukendt')} | Snit: `{nyeste.get('RATING_AVG', 0)}`")
        con = nyeste.get('KONTRAKT', nyeste.get('CONTRACT', ''))
        if pd.notna(con) and str(con).strip() != "":
            st.caption(f"Kontraktudløb: {con}")

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
            with st.expander(f"Dato: {row.get('DATO')} | Rating: {row.get('RATING_AVG')} | Scout: {row.get('SCOUT', 'Ukendt')}"):
                st.write(row.get('VURDERING'))

    with t3:
        if len(historik) > 1:
            fig_line = go.Figure(go.Scatter(x=historik['DATO_DT'], y=historik['RATING_AVG'], mode='lines+markers', line=dict(color='#df003b')))
            fig_line.update_layout(yaxis=dict(range=[0, 6]), height=300, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Kræver flere rapporter for at vise udvikling.")

    with t4:
        if career_df is not None and not career_df.empty:
            df_p = career_df[career_df['PLAYER_WYID'] == clean_p_id].copy()
            if not df_p.empty:
                mapping = {'SEASONNAME': 'Sæson', 'TEAMNAME': 'Klub', 'COMPETITIONNAME': 'Turnering', 'APPEARANCES': 'Kampe', 'GOAL': 'Mål'}
                st.dataframe(df_p[[c for c in mapping.keys() if c in df_p.columns]].rename(columns=mapping), use_container_width=True, hide_index=True)

    with t5:
        categories = ['Beslutning', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Leder', 'Teknik', 'Intelligens']
        cols = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        fig_radar = go.Figure(go.Scatterpolar(r=v + [v[0]], theta=categories + [categories[0]], fill='toself', line=dict(color='#df003b')))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False)
        st.plotly_chart(fig_radar, use_container_width=True)

def vis_side(scout_df, players_local, sql_players, career_df):
    if scout_df is None or scout_df.empty:
        st.info("Ingen spejder-rapporter fundet.")
        return
    
    # 1. KLARGØR SCOUTING DATA (DIN CSV)
    df = scout_df.copy()
    df.columns = [c.strip().upper() for c in df.columns]
    df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(rens_id)
    
    # 2. HENT DE UNIKKE BILLEDER FRA SQL (SNOWFLAKE)
    # Vi laver en ordbog baseret på PLAYER_WYID som nøgle
    billed_map = {}
    if sql_players is not None and not sql_players.empty:
        sql_df = sql_players.copy()
        sql_df.columns = [c.upper() for c in sql_df.columns]
        sql_df['PLAYER_WYID'] = sql_df['PLAYER_WYID'].apply(rens_id)
        
        # Vi tager kun rækker der har en valid URL
        valid_pics = sql_df[sql_df['IMAGEDATAURL'].notna()]
        billed_map = dict(zip(valid_pics['PLAYER_WYID'], valid_pics['IMAGEDATAURL']))

    # 3. FUNKTION DER HENTER DEN RIGTIGE URL
    def hent_korrekt_billede(row):
        pid = row.get('PLAYER_WYID')
        std_img = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
        
        # Tjek om vi har det unikke link fra SQL til netop dette PLAYER_WYID
        if pid in billed_map:
            return billed_map[pid]
        
        # Hvis ID ikke findes i SQL-udtrækket (f.eks. spiller i en anden liga), 
        # så bruger vi standard-silhuetten i stedet for at gætte på en URL
        return std_img

    # Påfør den unikke URL til hver række
    df['VIS_BILLEDE'] = df.apply(hent_korrekt_billede, axis=1)

    # 4. DATA-PROCESSERING
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    
    # Gruppér for at få den nyeste rapport pr. spiller
    f_df = df.sort_values('DATO_DT', ascending=True).groupby('PLAYER_WYID').tail(1).copy()
    
    # 5. TABEL-VISNING
    vis_cols = ['VIS_BILLEDE', 'NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'SCOUT']
    disp = f_df[vis_cols].copy()
    
    col_map = {
        'VIS_BILLEDE': ' ', 
        'NAVN': 'Navn', 
        'POSITION_VISNING': 'Pos', 
        'KLUB': 'Klub', 
        'RATING_AVG': 'Rating', 
        'STATUS': 'Status',
        'SCOUT': 'Scout'
    }
    
    event = st.dataframe(
        disp.rename(columns=col_map), 
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        height="content",
        column_config={
            " ": st.column_config.ImageColumn(" ", width="small"),
            "Rating": st.column_config.NumberColumn(format="%.1f")
        }
    )
    
    if len(event.selection.rows) > 0:
        valgt_index = event.selection.rows[0]
        # f_df indeholder 'VIS_BILLEDE', så det bliver sendt med ind i profilen
        spiller_data = f_df.iloc[valgt_index]
        vis_profil(spiller_data, df, career_df)
