import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    # Forbered navne-liste
    df_p = spillere.copy()
    if 'NAVN' not in df_p.columns:
        df_p['NAVN'] = df_p['FIRSTNAME'].fillna('') + " " + df_p['LASTNAME'].fillna('')
    
    navne_liste = sorted(df_p['NAVN'].unique())

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        p_info = df_p[df_p['NAVN'] == navn].iloc[0]
        pid = str(p_info['PLAYER_WYID']).split('.')[0] # Sikrer rent ID
        klub = p_info.get('TEAMNAME', 'Hvidovre IF')
        pos = p_info.get('POS', 'Ukendt')
        
        # Stats fra season_stats.csv
        stats = {}
        if not player_events.empty:
            st_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(pid)]
            if not st_match.empty:
                stats = st_match.iloc[0].to_dict()

        # Radar data fra scouting_db.csv
        tech = {k: 0 for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']}
        if not df_scout.empty:
            sc_row = df_scout[df_scout['NAVN'] == navn]
            if not sc_row.empty:
                n = sc_row.sort_values('DATO', ascending=False).iloc[0]
                for k in tech.keys(): tech[k] = n.get(k, 0)

        return pid, klub, pos, stats, tech

    id1, k1, pos1, st1, t1 = hent_info(s1_navn)
    id2, k2, pos2, st2, t2 = hent_info(s2_navn)

    # VISNING AF PROFILER
    def vis_profil(navn, pid, klub, pos, side, color):
        img_url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid}_100x130.png"
        if side == "venstre":
            c_img, c_txt = st.columns([1, 2])
            with c_img: st.image(img_url, width=100)
            with c_txt: 
                st.markdown(f"<h3 style='color:{color};'>{navn}</h3>", unsafe_allow_html=True)
                st.write(f"{pos} | {klub}")
        else:
            c_txt, c_img = st.columns([2, 1])
            with c_txt: 
                st.markdown(f"<h3 style='text-align:right; color:{color};'>{navn}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:right;'>{pos} | {klub}</p>", unsafe_allow_html=True)
            with c_img: st.image(img_url, width=100)

    col1, col2, col3 = st.columns([2, 3, 2])
    
    with col1: vis_profil(s1_navn, id1, k1, pos1, "venstre", "#df003b")
    
    with col2:
        # RADAR CHART - HER ER RETTELSEN TIL 8-KANT
        categories = ['Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 'Udholdenhed', 'Lederevner', 'Teknik', 'Spil-int.']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=[t1[k] for k in t1.keys()] + [list(t1.values())[0]], theta=categories + [categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=[t2[k] for k in t2.keys()] + [list(t2.values())[0]], theta=categories + [categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
        
        fig.update_layout(
            polar=dict(
                gridshape='linear', # <--- DETTE GØR DEN KANTET I STEDET FOR RUND
                radialaxis=dict(visible=True, range=[0, 6])
            ),
            showlegend=False,
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)

    with col3: vis_profil(s2_navn, id2, k2, pos2, "højre", "#0056a3")
