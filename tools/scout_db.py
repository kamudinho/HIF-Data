import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def rens_id(val):
    if pd.isna(val): return ""
    return str(val).split('.')[0].strip()

def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        v = float(str(val).replace(',', '.'))
        return int(v) if v <= 6 else 6
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
    
    # Header
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
                st.write(row.get('VURDERING', 'Ingen kommentar'))

    with t3:
        if len(historik) > 1:
            fig_line = go.Figure(go.Scatter(x=historik['DATO_DT'], y=historik['RATING_AVG'], mode='lines+markers', line=dict(color='#df003b')))
            fig_line.update_layout(yaxis=dict(range=[0, 6.5]), height=250, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Kræver flere rapporter.")

    with t4:
        st.subheader("Karriere Stats")
        if career_df is not None and not career_df.empty:
            # Sørg for at vi matcher på rensede ID'er
            df_p = career_df[career_df['PLAYER_WYID'].astype(str).str.contains(clean_p_id, na=False)].copy()
            
            if not df_p.empty:
                # Kolonne-mapping (Sørger for de navne du bad om)
                mapping = {
                    'SEASONNAME': 'Sæson',
                    'TEAMNAME': 'Hold',
                    'APPEARANCES': 'Kampe', # MATCHES hedder ofte APPEARANCES i WyScout Snowflake
                    'MINUTESPLAYED': 'Min', 
                    'GOAL': 'Mål',
                    'ASSIST': 'Assists',
                    'YELLOWCARDS': 'Gule',
                    'REDCARDS': 'Røde'
                }
                
                # Find de kolonner der faktisk findes i dit datasæt (Snowflake bruger tit store bogstaver)
                eksisterende_kolonner = {k: v for k, v in mapping.items() if k in df_p.columns}
                
                if eksisterende_kolonner:
                    disp_stats = df_p[list(eksisterende_kolonner.keys())].rename(columns=eksisterende_kolonner)
                    st.dataframe(disp_stats, use_container_width=True, hide_index=True)
                else:
                    st.warning("De ønskede stat-kolonner blev ikke fundet i Snowflake-data.")
            else:
                st.info("Ingen stats fundet for denne spiller.")
        else:
            st.error("Kunne ikke hente karriere-data fra Snowflake.")

    with t5:
        # RADAR CHART FIX
        categories = ['Beslutning', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Leder', 'Teknik', 'Intelligens']
        keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in keys]
        
        # Lukker cirklen
        v_radar = v + [v[0]]
        c_radar = categories + [categories[0]]
        
        fig_radar = go.Figure(go.Scatterpolar(
            r=v_radar, 
            theta=c_radar, 
            fill='toself', 
            fillcolor='rgba(223, 0, 59, 0.3)',
            line=dict(color='#df003b', width=2)
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 6], tickvals=[1,2,3,4,5,6])),
            showlegend=False, height=400, margin=dict(l=60, r=60, t=40, b=40)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

def vis_side(scout_df, players_local, sql_players, career_df):
    if scout_df is None or scout_df.empty:
        st.info("Ingen spejder-rapporter fundet.")
        return
    
    df = scout_df.copy()
    df.columns = [c.strip().upper() for c in df.columns]
    df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(rens_id)
    
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

    col_map = {'VIS_BILLEDE': ' ', 'NAVN': 'Navn', 'POSITION_VISNING': 'Pos', 'KLUB': 'Klub', 'RATING_AVG': 'Rating', 'STATUS': 'Status', 'SCOUT': 'Scout'}
    disp = f_df[list(col_map.keys())].rename(columns=col_map)
    
    calc_height = (len(disp) + 1) * 35 + 3
    
    event = st.dataframe(
        disp, 
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        height=min(calc_height, 500),
        column_config={
            " ": st.column_config.ImageColumn(" ", width="small"),
            "Rating": st.column_config.NumberColumn(format="%.1f")
        }
    )
    
    if len(event.selection.rows) > 0:
        valgt_index = event.selection.rows[0]
        spiller_data = f_df.iloc[valgt_index]
        vis_profil(spiller_data, df, career_df)
