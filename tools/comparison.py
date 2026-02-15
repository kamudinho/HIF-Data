import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

def map_position(pos_code):
    """Oversætter numeriske positionskoder til dansk tekst."""
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    s_code = str(pos_code).split('.')[0]
    return pos_map.get(s_code, s_code if s_code != "nan" else "Ukendt")

def vis_side(spillere, player_events, df_scout):
    # --- 1. SAMLE NAVNELISTE FRA BEGGE KILDER ---
    df_p = spillere.copy()
    if 'NAVN' not in df_p.columns and not df_p.empty:
        df_p['NAVN'] = df_p['FIRSTNAME'].fillna('') + " " + df_p['LASTNAME'].fillna('')
    
    df_s = df_scout.copy()
    
    # SIKKERHED: Sørg for at df_s har de rigtige kolonnenavne
    if 'ID' not in df_s.columns and 'PLAYER_WYID' in df_s.columns:
        df_s = df_s.rename(columns={'PLAYER_WYID': 'ID'})
    
    if 'NAVN' not in df_s.columns:
        df_s['NAVN'] = "Ukendt navn"

    # Lav lister til kombination (kun hvis kolonnerne findes)
    p_list = df_p[['NAVN', 'PLAYER_WYID']].rename(columns={'PLAYER_WYID': 'ID'}) if not df_p.empty else pd.DataFrame(columns=['NAVN', 'ID'])
    
    # Her fejlede den før - nu tjekker vi om 'ID' findes i df_s
    if 'ID' in df_s.columns:
        s_list = df_s[['NAVN', 'ID']]
    else:
        s_list = pd.DataFrame(columns=['NAVN', 'ID'])
    
    combined_names = pd.concat([p_list, s_list]).drop_duplicates(subset=['NAVN'])
    navne_liste = sorted(combined_names['NAVN'].unique())

    if not navne_liste:
        st.warning("Ingen spillere fundet i databaserne.")
        return

    # --- 2. SELECTBOX SEKTION ---
    st.markdown("<div style='padding-top: 10px; padding-bottom: 30px;'>", unsafe_allow_html=True)
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)
    st.markdown("</div>", unsafe_allow_html=True)

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
            pos = map_position(row.get('POS', 'Ukendt'))
            
            if not player_events.empty:
                # SIKKERHED: Håndter match på ID strengt
                st_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(pid, na=False)]
                if not st_match.empty:
                    stats_data = st_match.iloc[0].to_dict()

        if not s_match.empty:
            # Tag den nyeste rapport hvis der er flere
            n = s_match.sort_values(df_s.columns[0], ascending=False).iloc[0] 
            if pid == "0":
                pid = str(n.get('ID', '0')).split('.')[0].strip()
                klub = n.get('KLUB', 'Eget emne')
                pos = n.get('POSITION', 'Ukendt')
            
            for k in tech.keys():
                tech[k] = n.get(k, 0)
            
            scout_texts = {
                's': n.get('STYRKER', 'Ingen data'),
                'u': n.get('UDVIKLING', 'Ingen data'),
                'v': n.get('VURDERING', 'Ingen data')
            }

        return pid, klub, pos, stats_data, tech, scout_texts

    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    # --- HJÆLPEFUNKTIONER TIL VISNING ---
    def vis_spiller_billede(pid, w=100):
        url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid}_100x130.png"
        std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
        try:
            resp = requests.head(url, timeout=0.8)
            st.image(url if resp.status_code == 200 else std, width=w)
        except:
            st.image(std, width=w)

    def vis_profil_kolonne(navn, pid, klub, pos, stats, side, color):
        name_style = f"margin:0; padding:0; color:{color}; line-height:1.0; font-size:24px; font-weight:bold;"
        info_style = "margin:0; padding:0; color:gray; font-size:14px; line-height:1.0;"

        if side == "venstre":
            c_img, c_txt = st.columns([1, 2])
            with c_img: vis_spiller_billede(pid)
            with c_txt: 
                st.markdown(f"<div style='text-align:left;'><p style='{name_style}'>{navn}</p><p style='{info_style}'>{pos} | {klub}</p></div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns([1,1,1])
            m1.metric("KAMPE", int(float(stats.get('MATCHES', 0))))
            m2.metric("MIN.", int(float(stats.get('MINUTESPLAYED', 0))))
            m3.metric("MÅL", int(float(stats.get('GOALS', 0))))
        else:
            c_txt, c_img = st.columns([2, 1])
            with c_txt: 
                st.markdown(f"<div style='text-align:right;'><p style='{name_style}'>{navn}</p><p style='{info_style}'>{pos} | {klub}</p></div>", unsafe_allow_html=True)
            with c_img: vis_spiller_billede(pid)
            
            st.markdown("<br>", unsafe_allow_html=True)
            _, m1, m2, m3 = st.columns([0.5, 1, 1, 1])
            with m1: st.metric("KAMPE", int(float(stats.get('MATCHES', 0))))
            with m2: st.metric("MIN.", int(float(stats.get('MINUTESPLAYED', 0))))
            with m3: st.metric("MÅL", int(float(stats.get('GOALS', 0))))

    # --- 3. HOVED LAYOUT ---
    col1, col2, col3 = st.columns([3, 3, 3])
    with col1: vis_profil_kolonne(s1_navn, res1[0], res1[1], res1[2], res1[3], "venstre", "#df003b")
    
    with col2:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        categories = ['Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 'Udholdenhed', 'Lederevner', 'Teknik', 'Spil-int.']
        
        def get_vals(t):
            keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
            v = [t.get(k, 0) for k in keys]
            v.append(v[0])
            return v

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=get_vals(res1[4]), theta=categories + [categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=get_vals(res2[4]), theta=categories + [categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
        
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False, height=420, margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col3: vis_profil_kolonne(s2_navn, res2[0], res2[1], res2[2], res2[3], "højre", "#0056a3")

    # --- 4. SCOUTING TABS ---
    st.write("---")
    sc1, sc2 = st.columns(2)
    with sc1:
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t1.info(res1[5]['s']); t2.warning(res1[5]['u']); t3.success(res1[5]['v'])
    with sc2:
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t1.info(res2[5]['s']); t2.warning(res2[5]['u']); t3.success(res2[5]['v'])
