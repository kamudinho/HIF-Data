import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def rens_id(val):
    if pd.isna(val): return ""
    return str(val).split('.')[0].strip()

def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def map_position(row):
    pos_val = rens_id(row.get('POS', row.get('POSITION', '')))
    pos_dict = {"1": "MM", "2": "HB", "3": "VB", "4": "VCB", "5": "HCB", "6": "DMC", "7": "HK", "8": "MC", "9": "ANG", "10": "OMC", "11": "VK"}
    return pos_dict.get(pos_val, "Ukendt")

@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, career_df):
    clean_p_id = rens_id(p_data['PLAYER_WYID'])
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].copy()
    if 'DATO_DT' in historik.columns:
        historik = historik.sort_values('DATO_DT', ascending=True)
    nyeste = historik.iloc[-1]
    
    h1, h2 = st.columns([1, 4])
    with h1:
        st.image(p_data.get('VIS_BILLEDE', ""), width=115)
    with h2:
        st.markdown(f"## {nyeste.get('NAVN', 'Ukendt')}")
        st.caption(f"{nyeste.get('KLUB', 'Ingen klub')} | {nyeste.get('POSITION_VISNING', 'Ukendt')} | Snit: {nyeste.get('RATING_AVG', 0)}")

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
        if len(historik) > 1:
            fig_line = go.Figure(go.Scatter(x=historik['DATO_DT'], y=historik['RATING_AVG'], mode='lines+markers', line=dict(color='#df003b')))
            fig_line.update_layout(yaxis=dict(range=[0, 6]), height=250, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_line, use_container_width=True)

    with t4:
        if career_df is not None and not career_df.empty:
            df_p = career_df[career_df['PLAYER_WYID'] == clean_p_id].copy()
            st.dataframe(df_p, use_container_width=True, hide_index=True)

    with t5:
        categories = ['Beslutning', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Leder', 'Teknik', 'Intelligens']
        v = [rens_metrik_vaerdi(nyeste.get(c.upper(), 0)) for c in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']]
        fig_radar = go.Figure(go.Scatterpolar(r=v + [v[0]], theta=categories + [categories[0]], fill='toself', line=dict(color='#df003b')))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=300)
        st.plotly_chart(fig_radar, use_container_width=True)

def vis_side(scout_df, players_local, sql_players, career_df):
    if scout_df is None or scout_df.empty:
        st.info("Ingen spejder-rapporter fundet.")
        return
    
    df = scout_df.copy()
    df.columns = [c.strip().upper() for c in df.columns]
    df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(rens_id)
    
    # Image Map
    billed_map = {}
    if sql_players is not None and not sql_players.empty:
        billed_map = dict(zip(sql_players['PLAYER_WYID'], sql_players['IMAGEDATAURL']))

    df['VIS_BILLEDE'] = df['PLAYER_WYID'].apply(lambda x: billed_map.get(x, "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"))
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    
    f_df = df.sort_values('DATO_DT', ascending=True).groupby('PLAYER_WYID').tail(1).copy()
    
    search = st.text_input("Søg i databasen...", placeholder="Navn eller klub...")
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]

    # Tabel opsætning
    col_map = {'VIS_BILLEDE': ' ', 'NAVN': 'Navn', 'POSITION_VISNING': 'Pos', 'KLUB': 'Klub', 'RATING_AVG': 'Rating', 'STATUS': 'Status', 'SCOUT': 'Scout'}
    disp = f_df[list(col_map.keys())].rename(columns=col_map)
    
    # BEREGN DYNAMISK HØJDE (Sørger for at fjerne scrollbaren)
    calc_height = (len(disp) + 1) * 35 + 3
    
    event = st.dataframe(
        disp, 
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        height=calc_height, # Her fjernes scrollbaren
        column_config={
            " ": st.column_config.ImageColumn(" ", width="small"),
            "Rating": st.column_config.NumberColumn(format="%.1f")
        }
    )
    
    if len(event.selection.rows) > 0:
        valgt_index = event.selection.rows[0]
        spiller_data = f_df.iloc[valgt_index]
        vis_profil(spiller_data, df, career_df)
