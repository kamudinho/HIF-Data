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
    # POS fra players.csv
    pos_val = str(row.get('POS', '')).split('.')[0].strip()
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back", "4": "Midtstopper", 
        "5": "Midtstopper", "6": "Defensiv Midt", "7": "Højre Kant", "8": "Central Midt", 
        "9": "Angriber", "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    if pos_val in pos_dict: return pos_dict[pos_val]
    
    # Fallback til POSITION kolonnen fra din scouting_db.csv
    return str(row.get('POSITION', 'Ukendt'))

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
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].copy()
    
    if 'DATO_DT' in historik.columns:
        historik = historik.sort_values('DATO_DT', ascending=True)
    
    if historik.empty:
        st.error("Ingen rapporter fundet.")
        return
    
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
        contract_val = nyeste.get('KONTRAKT', nyeste.get('CONTRACT', ''))
        if pd.notna(contract_val) and str(contract_val).strip() != "":
            st.caption(f"Kontraktudløb: {contract_val}")

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
            dato_vis = row.get('DATO', 'Ukendt dato')
            with st.expander(f"Dato: {dato_vis} | Rating: {row.get('RATING_AVG')}"):
                st.write(row.get('VURDERING'))

    with t3:
        if 'DATO_DT' in historik.columns and len(historik) > 1:
            fig_line = go.Figure(go.Scatter(x=historik['DATO_DT'], y=historik['RATING_AVG'], mode='lines+markers', line=dict(color='#df003b')))
            fig_line.update_layout(yaxis=dict(range=[0, 6]), height=300, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Kræver mindst to rapporter for at vise udvikling.")

    with t4:
        if career_df is not None and not career_df.empty:
            df_p = career_df[career_df['PLAYER_WYID'] == clean_p_id].copy()
            if not df_p.empty:
                mapping = {'SEASONNAME': 'Sæson', 'TEAMNAME': 'Klub', 'COMPETITIONNAME': 'Turnering', 'APPEARANCES': 'Kampe', 'GOAL': 'Mål'}
                cols_to_show = [c for c in mapping.keys() if c in df_p.columns]
                st.dataframe(df_p[cols_to_show].rename(columns=mapping), use_container_width=True, hide_index=True)

    with t5:
        categories = ['Beslutning', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Leder', 'Teknik', 'Intelligens']
        cols = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        fig_radar = go.Figure(go.Scatterpolar(r=v + [v[0]], theta=categories + [categories[0]], fill='toself', line=dict(color='#df003b')))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False)
        st.plotly_chart(fig_radar, use_container_width=True)

def vis_side(scout_df, players_local, sql_players, career_df):
    st.title("Scouting Database")
    
    # 1. FORBERED DATA - Tving alle kolonnenavne til store bogstaver for at matche koden
    if scout_df is not None and not scout_df.empty:
        scout_df.columns = [c.upper() for c in scout_df.columns]
    
    for d in [scout_df, players_local, sql_players, career_df]:
        if d is not None and not d.empty and 'PLAYER_WYID' in d.columns:
            d['PLAYER_WYID'] = d['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
            
    # 2. BASE: Brug KUN scouting_db.csv
    if scout_df is None or scout_df.empty:
        st.info("Ingen spejder-rapporter fundet i databasen endnu.")
        return
    
    df = scout_df.copy()

    # SIKRING AF DATO_DT
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce').fillna(pd.Timestamp('2024-01-01'))

    # 3. LOOKUP: Flet stamdata på (Billeder fra SQL og Kontrakt fra players.csv)
    lookup = pd.DataFrame()
    if players_local is not None and not players_local.empty:
        lookup = players_local.copy()
        if sql_players is not None and not sql_players.empty:
            sql_img = sql_players[['PLAYER_WYID', 'IMAGEDATAURL']].drop_duplicates('PLAYER_WYID')
            lookup = lookup.merge(sql_img, on='PLAYER_WYID', how='left')
    elif sql_players is not None:
        lookup = sql_players.copy()

    if not lookup.empty:
        df = df.merge(lookup.drop_duplicates('PLAYER_WYID'), on='PLAYER_WYID', how='left', suffixes=('', '_extra'))

    # 4. KLARGØR VISNING
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    
    # Sorter efter dato og tag nyeste pr. spiller
    f_df = df.sort_values('DATO_DT', ascending=True).groupby('PLAYER_WYID').tail(1).copy()
    
    # Søgning
    search = st.text_input("Søg i databasen...", placeholder="Navn eller klub...")
    if search:
        mask = pd.Series(False, index=f_df.index)
        if 'NAVN' in f_df.columns: mask |= f_df['NAVN'].str.contains(search, case=False, na=False)
        if 'KLUB' in f_df.columns: mask |= f_df['KLUB'].str.contains(search, case=False, na=False)
        f_df = f_df[mask]

    # 5. TABELVISNING
    # Vi mapper dine specifikke kolonnenavne
    vis_cols = ['NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS']
    if 'IMAGEDATAURL' in f_df.columns:
        vis_cols.insert(0, 'IMAGEDATAURL')
    
    available_cols = [c for c in vis_cols if c in f_df.columns]
    disp = f_df[available_cols].copy()
    
    col_map = {
        'IMAGEDATAURL': ' ', 'NAVN': 'Navn', 'POSITION_VISNING': 'Pos', 
        'KLUB': 'Klub', 'RATING_AVG': 'Rating', 'STATUS': 'Status'
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
        vis_profil(f_df.iloc[event.selection.rows[0]], df, career_df)
