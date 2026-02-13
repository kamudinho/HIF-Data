import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

def vis_side(spillere, player_events, df_scout):
    # --- 1. SAMLE NAVNELISTE ---
    df_p = spillere.copy()
    if 'NAVN' not in df_p.columns and not df_p.empty:
        df_p['NAVN'] = df_p['FIRSTNAME'].fillna('') + " " + df_p['LASTNAME'].fillna('')
    
    df_s = df_scout.copy()
    if 'NAVN' not in df_s.columns:
        df_s['NAVN'] = "Ukendt navn"

    p_list = df_p[['NAVN', 'PLAYER_WYID']].rename(columns={'PLAYER_WYID': 'ID'}) if not df_p.empty else pd.DataFrame()
    s_list = df_s[['NAVN', 'ID']] if not df_s.empty else pd.DataFrame()
    
    combined_names = pd.concat([p_list, s_list]).drop_duplicates(subset=['NAVN'])
    navne_liste = sorted(combined_names['NAVN'].unique())

    if not navne_liste:
        st.warning("Ingen spillere fundet.")
        return

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        p_match = df_p[df_p['NAVN'] == navn]
        s_match = df_s[df_s['NAVN'] == navn]
        
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
                if not st_match.empty:
                    stats_data = st_match.iloc[0].to_dict()

        if not s_match.empty:
            n = s_match.sort_values('DATO', ascending=False).iloc[0]
            if pid == "0":
                pid = str(n.get('ID', '0')).split('.')[0].strip()
                klub = n.get('KLUB', 'Eget emne')
                pos = n.get('POSITION', 'Ukendt')
            for k in tech.keys():
                tech[k] = n.get(k, 0)
            scout_texts = {'s': n.get('STYRKER', 'Ingen data'), 'u': n.get('UDVIKLING', 'Ingen data'), 'v': n.get('VURDERING', 'Ingen data')}

        return pid, klub, pos, stats_data, tech, scout_texts

    id1, k1, pos1, st1, t1, txt1 = hent_info(s1_navn)
    id2, k2, pos2, st2, t2, txt2 = hent_info(s2_navn)

    # --- HJÆLPEFUNKTIONER ---
    def vis_spiller_billede(pid, w=100):
        url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid}_100x130.png"
        std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
        try:
            resp = requests.head(url, timeout=0.8)
            # ndplayer (std) gøres 8% mindre for at matche visuelt
            st.image(url if resp.status_code == 200 else std, width=w if resp.status_code == 200 else int(w*0.92))
        except:
            st.image(std, width=int(w*0.92))

    def vis_profil_kolonne(navn, pid, klub, pos, stats, side, color):
        # Definerer en fast stil for at sikre 100% ensartethed i font og højde
        name_style = f"margin:0; padding:0; color:{color}; line-height:1.0; font-size:24px; font-weight:bold;"
        info_style = "margin:0; padding:0; color:gray; font-size:14px; line-height:1.0;"

        if side == "venstre":
            # Spiller 1: Billede til venstre, tekst til højre
            c_img, c_txt = st.columns([1, 2])
            with c_img: 
                vis_spiller_billede(pid)
            with c_txt: 
                st.markdown(f"<div style='text-align:left;'><p style='{name_style}'>{navn}</p><p style='{info_style}'>{pos} | {klub}</p></div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            # Metrics flugter til venstre under spiller 1
            m1, m2, m3 = st.columns([1,1,1])
            m1.metric("KAMPE", int(float(stats.get('MATCHES', 0))))
            m2.metric("MIN.", int(float(stats.get('MINUTESPLAYED', 0))))
            m3.metric("MÅL", int(float(stats.get('GOALS', 0))))
        
        else:
            # Spiller 2: Tekst til venstre (højrestillet), billede til højre
            c_txt, c_img = st.columns([2, 1])
            with c_txt: 
                # Her tvinger vi teksten helt til højre i kolonnen
                st.markdown(f"<div style='text-align:right;'><p style='{name_style}'>{navn}</p><p style='{info_style}'>{pos} | {klub}</p></div>", unsafe_allow_html=True)
            with c_img: 
                vis_spiller_billede(pid)
            
            st.markdown("<br>", unsafe_allow_html=True)
            # Her skaber vi 3 smalle kolonner til højre for at tvinge metrics helt ud til kanten
            # Vi bruger 3 tomme spacer-kolonner først for at skubbe dem
            _, m1, m2, m3 = st.columns([0.5, 1, 1, 1])
            with m1: st.metric("KAMPE", int(float(stats.get('MATCHES', 0))))
            with m2: st.metric("MIN.", int(float(stats.get('MINUTESPLAYED', 0))))
            with m3: st.metric("MÅL", int(float(stats.get('GOALS', 0))))

    # --- LAYOUT ---
    col1, col2, col3 = st.columns([2.5, 3, 2.5])
    with col1: 
        vis_profil_kolonne(s1_navn, id1, k1, pos1, st1, "venstre", "#df003b")
    
    with col2:
        categories = ['Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 'Udholdenhed', 'Lederevner', 'Teknik', 'Spil-int.']
        fig = go.Figure()
        
        def get_vals(t):
            v = [t[k] for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']]
            v.append(v[0])
            return v

        fig.add_trace(go.Scatterpolar(r=get_vals(t1), theta=categories + [categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=get_vals(t2), theta=categories + [categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
        
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])),
            showlegend=False, height=400, margin=dict(l=30, r=30, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col3: 
        vis_profil_kolonne(s2_navn, id2, k2, pos2, st2, "højre", "#0056a3")

    st.write("---")
    sc1, sc2 = st.columns(2)
    with sc1:
        t_a, t_b, t_c = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t_a.info(txt1['s']); t_b.warning(txt1['u']); t_c.success(txt1['v'])
    with sc2:
        t_a, t_b, t_c = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t_a.info(txt2['s']); t_b.warning(txt2['u']); t_c.success(txt2['v'])
