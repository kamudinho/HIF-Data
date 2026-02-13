import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

def vis_side(spillere, player_events, df_scout):
    # --- 1. SAMLE NAVNELISTE FRA BEGGE KILDER ---
    # Spillere fra truppen (players.csv)
    df_p = spillere.copy()
    if 'NAVN' not in df_p.columns and not df_p.empty:
        df_p['NAVN'] = df_p['FIRSTNAME'].fillna('') + " " + df_p['LASTNAME'].fillna('')
    
    # Spillere fra scouting databasen (scouting_db.csv)
    df_s = df_scout.copy()
    # Vi sikrer os, at vi har de nødvendige kolonner i df_s
    if 'NAVN' not in df_s.columns:
        df_s['NAVN'] = "Ukendt navn"

    # Lav en samlet oversigt over NAVN og ID til selectbox
    p_list = df_p[['NAVN', 'PLAYER_WYID']].rename(columns={'PLAYER_WYID': 'ID'}) if not df_p.empty else pd.DataFrame()
    s_list = df_s[['NAVN', 'ID']] if not df_s.empty else pd.DataFrame()
    
    combined_names = pd.concat([p_list, s_list]).drop_duplicates(subset=['NAVN'])
    navne_liste = sorted(combined_names['NAVN'].unique())

    if not navne_liste:
        st.warning("Ingen spillere fundet i hverken players.csv eller scouting_db.csv")
        return

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        # Find ud af om spilleren er i truppen eller scouting DB
        p_match = df_p[df_p['NAVN'] == navn]
        s_match = df_s[df_s['NAVN'] == navn]
        
        # Standard værdier
        pid = "0"
        klub = "Ukendt"
        pos = "Ukendt"
        stats_data = {}
        tech = {k: 0 for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']}
        scout_texts = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen data'}

        if not p_match.empty:
            # HENT FRA TRUPPEN
            row = p_match.iloc[0]
            pid = str(row['PLAYER_WYID']).split('.')[0].strip()
            klub = row.get('TEAMNAME', 'Hvidovre IF')
            pos = row.get('POS', 'Ukendt')
            
            # Hent kamp-stats
            if not player_events.empty:
                st_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(pid)]
                if not st_match.empty:
                    stats_data = st_match.iloc[0].to_dict()

        # HENT SCOUTING DATA (Også hvis spilleren findes i begge)
        if not s_match.empty:
            # Tag den nyeste rapport
            n = s_match.sort_values('DATO', ascending=False).iloc[0]
            if pid == "0": # Hvis ikke i truppen, brug ID fra scouting_db
                pid = str(n.get('ID', '0')).split('.')[0].strip()
                klub = n.get('KLUB', 'Eget emne')
                pos = n.get('POSITION', 'Ukendt')
            
            # Overskriv radar-værdier med scouting vurderingen
            for k in tech.keys():
                tech[k] = n.get(k, 0)
            
            scout_texts = {
                's': n.get('STYRKER', 'Ingen data'),
                'u': n.get('UDVIKLING', 'Ingen data'),
                'v': n.get('VURDERING', 'Ingen data')
            }

        return pid, klub, pos, stats_data, tech, scout_texts

    id1, k1, pos1, st1, t1, txt1 = hent_info(s1_navn)
    id2, k2, pos2, st2, t2, txt2 = hent_info(s2_navn)

    # --- HJÆLPEFUNKTIONER TIL VISNING ---
    def vis_spiller_billede(pid, w=110):
        url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid}_100x130.png"
        standard_url = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
        try:
            response = requests.head(url, timeout=1)
            st.image(url if response.status_code == 200 else standard_url, width=w)
        except:
            st.image(standard_url, width=w)

    def vis_profil_kolonne(navn, pid, klub, pos, stats, side, color):
        if side == "venstre":
            c_img, c_txt = st.columns([1, 2])
            with c_img: vis_spiller_billede(pid)
            with c_txt: 
                st.markdown(f"<h3 style='color:{color}; margin-bottom:0;'>{navn}</h3>", unsafe_allow_html=True)
                st.caption(f"{pos} | {klub}")
        else:
            c_txt, c_img = st.columns([2, 1])
            with c_txt: 
                st.markdown(f"<h3 style='text-align:right; color:{color}; margin-bottom:0;'>{navn}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:right; color:gray;'>{pos} | {klub}</p>", unsafe_allow_html=True)
            with c_img: vis_spiller_billede(pid)

        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("KAMPE", int(float(stats.get('MATCHES', 0))))
        m2.metric("MIN.", int(float(stats.get('MINUTESPLAYED', 0))))
        m3.metric("MÅL", int(float(stats.get('GOALS', 0))))

    # --- LAYOUT ---
    col1, col2, col3 = st.columns([2.5, 3, 2.5])
    with col1: vis_profil_kolonne(s1_navn, id1, k1, pos1, st1, "venstre", "#df003b")
    
    with col2:
        categories = ['Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 'Udholdenhed', 'Lederevner', 'Teknik', 'Spil-int.']
        fig = go.Figure()
        r1 = [t1[k] for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']]
        r1.append(r1[0])
        r2 = [t2[k] for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']]
        r2.append(r2[0])
        theta = categories + [categories[0]]
        fig.add_trace(go.Scatterpolar(r=r1, theta=theta, fill='toself', name=s1_navn, line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=r2, theta=theta, fill='toself', name=s2_navn, line_color='#0056a3'))
        fig.update_layout(polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col3: vis_profil_kolonne(s2_navn, id2, k2, pos2, st2, "højre", "#0056a3")

    st.write("---")
    sc1, sc2 = st.columns(2)
    with sc1:
        t_a, t_b, t_c = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t_a.info(txt1['s']); t_b.warning(txt1['u']); t_c.success(txt1['v'])
    with sc2:
        t_a, t_b, t_c = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t_a.info(txt2['s']); t_b.warning(txt2['u']); t_c.success(txt2['v'])
