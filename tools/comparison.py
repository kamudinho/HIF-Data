import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

# --- HJÆLPEFUNKTIONER ---
def map_position(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    s_code = str(pos_code).split('.')[0]
    return pos_map.get(s_code, s_code if s_code != "nan" else "Ukendt")

def vis_spiller_billede(pid, w=100):
    pid_clean = str(pid).split('.')[0].strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except:
        st.image(std, width=w)

def vis_side(spillere, player_events, df_scout):
    # 0. Sørg for at alle kolonnenavne er UPPERCASE
    for d in [spillere, player_events, df_scout]:
        if d is not None: d.columns = [c.upper() for c in d.columns]

    # 1. Forbered navnelister
    df_p = spillere.copy() if spillere is not None else pd.DataFrame()
    if not df_p.empty and 'NAVN' not in df_p.columns:
        df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
    
    df_s = df_scout.copy() if df_scout is not None else pd.DataFrame()
    if not df_s.empty and 'ID' not in df_s.columns and 'PLAYER_WYID' in df_s.columns:
        df_s = df_s.rename(columns={'PLAYER_WYID': 'ID'})

    # Kombiner navne fra Truppen og Scouting-databasen
    p_ids = df_p[['NAVN', 'PLAYER_WYID']].rename(columns={'PLAYER_WYID': 'ID'}) if not df_p.empty else pd.DataFrame()
    s_ids = df_s[['NAVN', 'ID']] if not df_s.empty else pd.DataFrame()
    combined = pd.concat([p_ids, s_ids]).drop_duplicates(subset=['NAVN'])
    navne_liste = sorted(combined['NAVN'].unique())

    if not navne_liste:
        st.warning("Ingen data fundet.")
        return

    # 2. UI: Vælg spillere
    st.markdown("### ⚖️ Spillersammenligning")
    c_sel1, c_sel2 = st.columns(2)
    with c_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with c_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        # Find ID i enten trup eller scout-liste
        match = combined[combined['NAVN'] == navn]
        pid = str(match.iloc[0]['ID']).split('.')[0].strip() if not match.empty else "0"
        
        # Hent basis info (Klub/Pos)
        p_data = df_p[df_p['NAVN'] == navn]
        klub = p_data.iloc[0].get('TEAMNAME', 'Ukendt') if not p_data.empty else "Eksternt emne"
        pos = map_position(p_data.iloc[0].get('POS', '')) if not p_data.empty else "Ukendt"

        # --- PLAYERSTATS AGGREGERING ---
        stats = {'KAMPE': 0, 'MIN': 0, 'MÅL': 0, 'ASS': 0}
        if player_events is not None and not player_events.empty:
            # Matcher på ID (vi renser ID kolonnen for at være sikre)
            p_stats = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(pid, na=False)]
            if not p_stats.empty:
                stats['KAMPE'] = p_stats['MATCHES'].sum()
                stats['MIN'] = p_stats['MINUTESTAGGED'].sum()
                stats['MÅL'] = p_stats['GOALS'].sum()
                stats['ASS'] = p_stats.get('ASSISTS', pd.Series([0])).sum()

        # --- SCOUTING DATA (Radar & Tekst) ---
        tech = {k: 0 for k in ['TEKNIK', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'BESLUTSOMHED', 'SPILINTELLIGENS']}
        scout_txt = {'s': '-', 'u': '-', 'v': '-'}
        
        if not df_s.empty:
            s_match = df_s[df_s['NAVN'] == navn]
            if not s_match.empty:
                # Tag nyeste rapport
                n = s_match.iloc[-1]
                if klub == "Eksternt emne": klub = n.get('KLUB', 'Ukendt')
                for k in tech.keys():
                    try: tech[k] = float(str(n.get(k, 0)).replace(',', '.'))
                    except: tech[k] = 0
                scout_txt = {'s': n.get('STYRKER', '-'), 'u': n.get('UDVIKLING', '-'), 'v': n.get('VURDERING', '-')}

        return pid, klub, pos, stats, tech, scout_txt

    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    # 3. VISNING
    col1, col2, col3 = st.columns([3, 4, 3])

    def vis_profil(navn, res, side, color):
        pid, klub, pos, stats, _, _ = res
        align = "left" if side == "venstre" else "right"
        
        # Header med billede
        c1, c2 = (st.columns([1, 2]) if side == "venstre" else st.columns([2, 1]))
        with (c1 if side == "venstre" else c2): vis_spiller_billede(pid)
        with (c2 if side == "venstre" else c1):
            st.markdown(f"<div style='text-align:{align};'><h3 style='color:{color}; margin:0;'>{navn}</h3><p style='color:gray;'>{pos}<br>{klub}</p></div>", unsafe_allow_html=True)
        
        # Stats blok
        st.markdown("<br>", unsafe_allow_html=True)
        m_cols = st.columns(3)
        m_cols[0].metric("KAMPE", int(stats['KAMPE']))
        m_cols[1].metric("MIN.", int(stats['MIN']))
        m_cols[2].metric("MÅL", int(stats['MÅL']))

    with col1: vis_profil(s1_navn, res1, "venstre", "#df003b")
    with col3: vis_profil(s2_navn, res2, "højre", "#0056a3")

    with col2:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        
        # Dine 8 originale kategorier
        categories = [
            'Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 
            'Udholdenhed', 'Lederevner', 'Teknik', 'Spil-int.'
        ]
        
        def get_vals(t):
            # Mapper direkte til dine kolonnenavne i databasen
            keys = [
                'BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 
                'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS'
            ]
            v = [t.get(k, 0) for k in keys]
            v.append(v[0]) # Lukker 8-kanten
            return v

        fig = go.Figure()
        
        # Spiller 1 (Rød)
        fig.add_trace(go.Scatterpolar(
            r=get_vals(res1[4]), 
            theta=categories + [categories[0]], 
            fill='toself', 
            name=s1_navn, 
            line_color='#df003b'
        ))
        
        # Spiller 2 (Blå)
        fig.add_trace(go.Scatterpolar(
            r=get_vals(res2[4]), 
            theta=categories + [categories[0]], 
            fill='toself', 
            name=s2_navn, 
            line_color='#0056a3'
        ))
        
        fig.update_layout(
            polar=dict(
                gridshape='linear', 
                radialaxis=dict(visible=True, range=[0, 6]) # Din oprindelige skala
            ),
            showlegend=False, 
            height=420, 
            margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    # 4. SCOUTING NOTER
    st.divider()
    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        t = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t[0].info(res1[5]['s']); t[1].warning(res1[5]['u']); t[2].success(res1[5]['v'])
    with sc_col2:
        t = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t[0].info(res2[5]['s']); t[1].warning(res2[5]['u']); t[2].success(res2[5]['v'])
