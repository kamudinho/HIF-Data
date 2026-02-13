import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

def vis_side(spillere, player_events, df_scout):
    # --- 1. SAMLE NAVNELISTE MED KILDE-BADGES ---
    df_p = spillere.copy()
    if 'NAVN' not in df_p.columns and not df_p.empty:
        df_p['NAVN'] = df_p['FIRSTNAME'].fillna('') + " " + df_p['LASTNAME'].fillna('')
    
    df_s = df_scout.copy()
    
    # Skab lister med badges
    p_options = [f"{n} (Trup)" for n in df_p['NAVN'].unique()] if not df_p.empty else []
    s_options = [f"{n} (Scout)" for n in df_s['NAVN'].unique()] if not df_s.empty else []
    
    navne_liste = sorted(list(set(p_options + s_options)))

    if not navne_liste:
        st.warning("Ingen spillere fundet.")
        return

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: s1_valg = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2: s2_valg = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(valg):
        rent_navn = valg.replace(" (Trup)", "").replace(" (Scout)", "")
        p_match = df_p[df_p['NAVN'] == rent_navn]
        s_match = df_s[df_s['NAVN'] == rent_navn]
        
        pid, klub, pos = "0", "Ukendt", "Ukendt"
        stats_data = {}
        tech = {k: 0 for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']}
        scout_texts = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen data'}

        if not p_match.empty:
            row = p_match.iloc[0]
            pid = str(row['PLAYER_WYID']).split('.')[0].strip()
            klub = row.get('TEAMNAME', 'Hvidovre IF')
            pos = row.get('POS', 'Ukendt')
            if not player_events.empty:
                st_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(pid)]
                if not st_match.empty: stats_data = st_match.iloc[0].to_dict()

        if not s_match.empty:
            n = s_match.sort_values('DATO', ascending=False).iloc[0]
            if pid == "0":
                pid = str(n.get('ID', '0')).split('.')[0].strip()
                klub = n.get('KLUB', 'Eget emne')
                pos = n.get('POSITION', 'Ukendt')
            for k in tech.keys(): tech[k] = n.get(k, 0)
            scout_texts = {'s': n.get('STYRKER', 'nan'), 'u': n.get('UDVIKLING', 'nan'), 'v': n.get('VURDERING', 'nan')}

        return rent_navn, pid, klub, pos, stats_data, tech, scout_texts

    res1 = hent_info(s1_valg)
    res2 = hent_info(s2_valg)

    # --- SIKKER BILLEDFUNKTION ---
    def vis_spiller_billede(pid):
        url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid}_100x130.png"
        std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
        try:
            resp = requests.head(url, timeout=0.8)
            # Vi bruger en fast bredde på 100 for at sikre ensartethed
            st.image(url if resp.status_code == 200 else std, width=100)
        except:
            st.image(std, width=70) # ndplayer justeres 8% ned for visuel match

    # --- SYMMETRISK PROFIL-LAYOUT ---
    def vis_profil_boks(data, color):
        navn, pid, klub, pos, stats, tech, txt = data
        
        # Ensartet layout: Billede til venstre, Info til højre
        c_img, c_txt = st.columns([1, 2])
        with c_img:
            vis_spiller_billede(pid)
        with c_txt:
            st.markdown(f"<h3 style='color:{color}; margin-bottom:0;'>{navn}</h3>", unsafe_allow_html=True)
            st.caption(f"{pos} | {klub}")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Metrics horisontalt
            m1, m2, m3 = st.columns(3)
            m1.metric("KAMPE", int(float(stats.get('MATCHES', 0))))
            m2.metric("MIN.", int(float(stats.get('MINUTESPLAYED', 0))))
            m3.metric("MÅL", int(float(stats.get('GOALS', 0))))

    # --- HOVED LAYOUT ---
    col1, col2, col3 = st.columns([2.5, 3, 2.5])
    
    with col1:
        vis_profil_boks(res1, "#df003b")
    
    with col2:
        # Radar Chart (8-kantet/linear)
        categories = ['Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 'Udholdenhed', 'Lederevner', 'Teknik', 'Spil-int.']
        fig = go.Figure()
        
        for r_data, name, color in [(res1[5], res1[0], "#df003b"), (res2[5], res2[0], "#0056a3")]:
            vals = [r_data[k] for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']]
            vals.append(vals[0])
            fig.add_trace(go.Scatterpolar(r=vals, theta=categories + [categories[0]], fill='toself', name=name, line_color=color))
            
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])),
            showlegend=False, height=400, margin=dict(l=30, r=30, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        vis_profil_boks(res2, "#0056a3")

    # --- SCOUTING TABS ---
    st.write("---")
    sc1, sc2 = st.columns(2)
    for col, data in [(sc1, res1[6]), (sc2, res2[6])]:
        with col:
            t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
            t1.info(data['s']); t2.warning(data['u']); t3.success(data['v'])
