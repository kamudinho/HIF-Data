import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere.empty:
        st.error("Kunne ikke finde spillerdata")
        return

    # --- FORBERED NAVNE ---
    df_p = spillere.copy()
    if 'NAVN' not in df_p.columns:
        df_p['NAVN'] = df_p['FIRSTNAME'].fillna('') + " " + df_p['LASTNAME'].fillna('')
    
    navne_liste = sorted(df_p['NAVN'].unique())

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        p_info = df_p[df_p['NAVN'] == navn].iloc[0]
        # VIGTIGT: Vi tvinger ID til at være en ren tekst-streng uden .0
        raw_id = str(p_info['PLAYER_WYID']).split('.')[0].strip()
        
        klub = p_info.get('TEAMNAME', 'Hvidovre IF')
        pos = p_info.get('POS', 'Ukendt')
        
        # Hent Stats fra season_stats.csv
        stats_data = {}
        if not player_events.empty:
            # Vi matcher på ID
            match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(raw_id)]
            if not match.empty:
                stats_data = match.iloc[0].to_dict()

        # Hent Radar-værdier fra scouting_db.csv
        tech = {k: 0 for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']}
        if not df_scout.empty:
            sc_row = df_scout[df_scout['NAVN'] == navn]
            if not sc_row.empty:
                n = sc_row.sort_values('DATO', ascending=False).iloc[0]
                for k in tech.keys(): tech[k] = n.get(k, 0)

        return raw_id, klub, pos, stats_data, tech

    id1, k1, pos1, st1, t1 = hent_info(s1_navn)
    id2, k2, pos2, st2, t2 = hent_info(s2_navn)

    # --- VISNINGS FUNKTION ---
    def vis_profil_kolonne(navn, pid, klub, pos, stats, side, color):
        # Wyscout billed-logik
        img_url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid}_100x130.png"
        
        if side == "venstre":
            c_img, c_txt = st.columns([1, 2])
            with c_img: st.image(img_url, width=110, fallback="https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png")
            with c_txt: 
                st.markdown(f"<h3 style='color:{color}; margin-bottom:0;'>{navn}</h3>", unsafe_allow_html=True)
                st.caption(f"{pos} | {klub}")
        else:
            c_txt, c_img = st.columns([2, 1])
            with c_txt: 
                st.markdown(f"<h3 style='text-align:right; color:{color}; margin-bottom:0;'>{navn}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:right; color:gray;'>{pos} | {klub}</p>", unsafe_allow_html=True)
            with c_img: st.image(img_url, width=110, fallback="https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Her genindfører vi METRICS (Stats)
        m1, m2, m3 = st.columns(3)
        # Vi bruger .get() for at undgå fejl hvis kolonnen mangler
        m1.metric("KAMPE", int(float(stats.get('MATCHES', 0))))
        m2.metric("MINUTTER", int(float(stats.get('MINUTESPLAYED', 0))))
        m3.metric("MÅL", int(float(stats.get('GOALS', 0))))

    # --- HOVED LAYOUT ---
    col1, col2, col3 = st.columns([2.5, 3, 2.5])
    
    with col1:
        vis_profil_kolonne(s1_navn, id1, k1, pos1, st1, "venstre", "#df003b")
    
    with col2:
        # Radar Chart (Polygon/8-kant)
        categories = ['Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 'Udholdenhed', 'Lederevner', 'Teknik', 'Spil-int.']
        fig = go.Figure()
        
        # Data runder af (lukker cirklen)
        r1 = [t1[k] for k in t1.keys()]
        r1.append(r1[0])
        r2 = [t2[k] for k in t2.keys()]
        r2.append(r2[0])
        theta = categories + [categories[0]]

        fig.add_trace(go.Scatterpolar(r=r1, theta=theta, fill='toself', name=s1_navn, line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=r2, theta=theta, fill='toself', name=s2_navn, line_color='#0056a3'))
        
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])),
            showlegend=False,
            height=450,
            margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        vis_profil_kolonne(s2_navn, id2, k2, pos2, st2, "højre", "#0056a3")
