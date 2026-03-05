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
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].copy()
    
    if 'DATO_DT' in historik.columns:
        historik = historik.sort_values('DATO_DT', ascending=True)
    
    nyeste = historik.iloc[-1]
    
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
    
    df = scout_df.copy()
    df.columns = [c.strip().upper() for c in df.columns]
    
    # Standard placeholder fra Wyscout
    std_img = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    
    # 1. RENS ID'ER (VIGTIGT: Vi fjerner .0 her, så URL'en bliver valid)
    df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(rens_id)
    
    # 2. Håndter stamdata og billeder fra SQL/Lokal
    if players_local is not None and not players_local.empty:
        p_local = players_local.copy()
        p_local.columns = [c.upper() for c in p_local.columns]
        p_local['PLAYER_WYID'] = p_local['PLAYER_WYID'].apply(rens_id)
        
        # Flet SQL billeder på hvis de findes
        if sql_players is not None and not sql_players.empty:
            sql_p = sql_players.copy()
            sql_p['PLAYER_WYID'] = sql_p['PLAYER_WYID'].apply(rens_id)
            sql_img = sql_p[['PLAYER_WYID', 'IMAGEDATAURL']].drop_duplicates('PLAYER_WYID')
            p_local = p_local.merge(sql_img, on='PLAYER_WYID', how='left')
            
        df = df.merge(p_local.drop_duplicates('PLAYER_WYID'), on='PLAYER_WYID', how='left', suffixes=('', '_extra'))

    # 3. DEN DEFINITIVE BILLEDE-LOGIK
    def get_final_img(row):
        # Tjek alle tænkelige kolonnenavne for en eksisterende URL
        url = row.get('IMAGEDATAURL', row.get('PLAYER_IMAGEDATAURL', row.get('IMAGE_URL')))
        
        if pd.notna(url) and str(url).startswith('http'):
            return url
        
        # Hvis ingen URL er gemt, byg den direkte fra Wyscouts CDN ved hjælp af ID
        pid = rens_id(row.get('PLAYER_WYID'))
        if pid and pid != "" and pid != "nan":
            # Dette er standard-formatet for Wyscouts offentlige billeder
            return f"https://cdn5.wyscout.com/photos/players/public/g-{pid}_100x130.png"
        
        return std_img

    df['BILLED_URL'] = df.apply(get_final_img, axis=1)

    # 4. DATA-PROCESSERING (Position, Dato, Nyeste rapport)
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    f_df = df.sort_values('DATO_DT', ascending=True).groupby('PLAYER_WYID').tail(1).copy()
    
    # 5. SØGNING
    search = st.text_input("Søg i databasen...", placeholder="Søg på navn, klub eller status...")
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | 
                    f_df['KLUB'].str.contains(search, case=False, na=False)]

    # 6. TABEL-VISNING
    vis_cols = ['BILLED_URL', 'NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'SCOUT']
    disp = f_df[vis_cols].copy()
    
    col_map = {
        'BILLED_URL': ' ', 
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
        vis_profil(f_df.iloc[event.selection.rows[0]], df, career_df)
