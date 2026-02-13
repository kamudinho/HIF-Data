import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere.empty:
        st.error("Kunne ikke finde spillerdata i data/players.csv")
        return

    # --- FORBERED DATA ---
    df_p = spillere.copy()
    # Vi sikrer os at vi har en NAVN kolonne
    if 'NAVN' not in df_p.columns:
        df_p['NAVN'] = df_p['FIRSTNAME'].fillna('') + " " + df_p['LASTNAME'].fillna('')
    
    # Saml alle mulige spillernavne (Truppen + Scoutere)
    hif_navne = df_p[['NAVN', 'PLAYER_WYID']]
    scout_navne = df_scout[['NAVN', 'ID']].rename(columns={'ID': 'PLAYER_WYID'}) if not df_scout.empty else pd.DataFrame()
    
    samlet_df = pd.concat([hif_navne, scout_navne]).drop_duplicates(subset=['NAVN'])
    navne_liste = sorted(samlet_df['NAVN'].unique())

    # --- UI VALG ---
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    # --- DATA HENTNING ---
    def hent_info(navn):
        match = samlet_df[samlet_df['NAVN'] == navn].iloc[0]
        pid = str(match['PLAYER_WYID'])
        
        # Find grunddata i players.csv
        p_info = df_p[df_p['PLAYER_WYID'] == pid]
        if not p_info.empty:
            klub = p_info['TEAMNAME'].iloc[0]
            pos = p_info['POS'].iloc[0]
        else:
            # Fallback til scouting_db
            s_info = df_scout[df_scout['NAVN'] == navn]
            klub = s_info['KLUB'].iloc[0] if 'KLUB' in s_info.columns else "Scouted"
            pos = s_info['POSITION'].iloc[0] if 'POSITION' in s_info.columns else "Ukendt"

        # Find stats i season_stats.csv
        stats = {}
        if not player_events.empty:
            st_match = player_events[player_events['PLAYER_WYID'] == pid]
            if not st_match.empty:
                stats = st_match.iloc[0].to_dict()

        # Find radar data i scouting_db
        tech = {k: 0 for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']}
        scout_txt = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen data'}
        if not df_scout.empty:
            sc_row = df_scout[df_scout['NAVN'] == navn]
            if not sc_row.empty:
                n = sc_row.sort_values('DATO', ascending=False).iloc[0]
                for k in tech.keys(): tech[k] = n.get(k, 0)
                scout_txt = {'s': n.get('STYRKER',''), 'u': n.get('UDVIKLING',''), 'v': n.get('VURDERING','')}

        return pid, klub, pos, stats, tech, scout_txt

    id1, k1, pos1, st1, tech1, txt1 = hent_info(s1_navn)
    id2, k2, pos2, st2, tech2, txt2 = hent_info(s2_navn)

    # --- VISNING ---
    def vis_box(navn, pid, klub, pos, stats, side, color):
        img = f"https://cdn5.wyscout.com/photos/players/public/g-{pid}_100x130.png"
        if side == "venstre":
            c_img, c_txt = st.columns([1, 2.5])
            with c_img: st.image(img, width=90)
            with c_txt: 
                st.markdown(f"<h3 style='color:{color};'>{navn}</h3>", unsafe_allow_html=True)
                st.caption(f"{pos} | {klub}")
        else:
            c_txt, c_img = st.columns([2.5, 1])
            with c_txt: 
                st.markdown(f"<h3 style='text-align:right; color:{color};'>{navn}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:right;'>{pos} | {klub}</p>", unsafe_allow_html=True)
            with c_img: st.image(img, width=90)
        
        st.write("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("KAMPE", int(stats.get('MATCHES', 0)))
        m2.metric("MIN.", int(stats.get('MINUTESPLAYED', 0)))
        m3.metric("MÅL", int(stats.get('GOALS', 0)))

    # Layout Grid
    c1, c2, c3 = st.columns([2.2, 3, 2.2])
    with c1: vis_box(s1_navn, id1, k1, pos1, st1, "venstre", "#df003b")
    with c2:
        # Radar Chart
        categories = ['Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 'Udholdenhed', 'Lederevner', 'Teknik', 'Spil-int.']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=[tech1[k] for k in tech1] + [tech1['BESLUTSOMHED']], theta=categories + [categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=[tech2[k] for k in tech2] + [tech2['BESLUTSOMHED']], theta=categories + [categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
    with c3: vis_box(s2_navn, id2, k2, pos2, st2, "højre", "#0056a3")

    # Scouting Tabs
    st.write("---")
    ts1, ts2 = st.columns(2)
    with ts1:
        t_a, t_b, t_c = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t_a.info(txt1['s']); t_b.warning(txt1['u']); t_c.success(txt1['v'])
    with ts2:
        t_a, t_b, t_c = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t_a.info(txt2['s']); t_b.warning(txt2['u']); t_c.success(txt2['v'])
