import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Fast konfiguration - matcher din app-standard
SEASON_FILTER = "2025/2026"

def map_position(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant",
        "GKP": "Målmand", "DEF": "Forsvar", "MID": "Midtbane", "FWD": "Angreb"
    }
    s_code = str(pos_code).split('.')[0].upper()
    return pos_map.get(s_code, "Ukendt")

def vis_spiller_billede(img_url, w=110):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    if pd.isna(img_url) or str(img_url).strip() in ["", "nan", "None"]:
        st.image(std, width=w)
    else:
        st.image(img_url, width=w)

def vis_side(df_spillere, d1, d2, career_df, d3):
    # --- 1. DATA FORBEREDELSE ---
    df_p = df_spillere.copy() if df_spillere is not None else pd.DataFrame()
    if not df_p.empty:
        df_p.columns = [c.upper() for c in df_p.columns]
        if 'NAVN' not in df_p.columns:
            df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
            df_p['NAVN'] = df_p['NAVN'].replace('', df_p.get('PLAYER_NAME', 'Ukendt'))
        df_p['PID_CLEAN'] = df_p['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s.columns = [c.upper().strip() for c in df_s.columns]
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    except:
        df_s = pd.DataFrame()

    # Navneliste til dropdowns
    navne_fra_trup = df_p['NAVN'].dropna().unique().tolist() if not df_p.empty else []
    navne_fra_scout = df_s['NAVN'].dropna().unique().tolist() if not df_s.empty else []
    navne_liste = sorted(list(set(navne_fra_trup + navne_fra_scout)))

    if not navne_liste:
        st.warning("⚠️ Ingen spillere fundet i systemet.")
        return

    # --- 2. UI SELECTORS ---
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0, key="comp_s1")
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1), key="comp_s2")

    def hent_data(navn):
        pid = None
        if not df_p.empty and navn in df_p['NAVN'].values:
            pid = df_p[df_p['NAVN'] == navn].iloc[0]['PID_CLEAN']
        elif not df_s.empty and navn in df_s['NAVN'].values:
            pid = df_s[df_s['NAVN'] == navn].iloc[0]['PID_CLEAN']
        
        if not pid: return None

        img, klub, pos = None, "Ukendt", "Ukendt"
        if not df_p.empty:
            match = df_p[df_p['PID_CLEAN'] == pid]
            if not match.empty:
                img = match.iloc[0].get('IMAGEDATAURL')
                klub = match.iloc[0].get('TEAMNAME', 'Hvidovre IF')
                pos = map_position(match.iloc[0].get('ROLECODE3', ''))
        
        stats = {'M': 0, 'K': 0}
        if career_df is not None and not career_df.empty:
            cdf = career_df.copy()
            cdf.columns = [c.upper() for c in cdf.columns]
            cdf['PID_CLEAN'] = cdf['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
            c_match = cdf[(cdf['PID_CLEAN'] == pid) & (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            if not c_match.empty:
                stats = {'M': c_match.iloc[0].get('GOAL', 0), 'K': c_match.iloc[0].get('APPEARANCES', 0)}

        # Radar Ratings - Her bruger vi de præcise keys fra din debug
        r = {k: 0.1 for k in ['FART', 'TEKNIK', 'BESLUT', 'INTEL', 'AGGR', 'LEDER', 'ATT', 'UDH']}
        if not df_s.empty:
            s_match = df_s[df_s['PID_CLEAN'] == pid]
            if not s_match.empty:
                n = s_match.iloc[-1] 
                r = {
                    'FART': n.get('FART', 0.1),
                    'TEKNIK': n.get('TEKNIK', 0.1),
                    'BESLUT': n.get('BESLUT', 0.1),
                    'INTEL': n.get('INTEL', 0.1),
                    'AGGR': n.get('AGGR', 0.1),
                    'LEDER': n.get('LEDER', 0.1),
                    'ATT': n.get('ATT', 0.1),
                    'UDH': n.get('UDH', 0.1) # Rettet fra UDHOLDENHED til UDH for at matche din CSV
                }
        return {"navn": navn, "img": img, "klub": klub, "pos": pos, "stats": stats, "r": r}

    data1 = hent_data(s1_navn)
    data2 = hent_data(s2_navn)

    # --- 3. VISUALISERING ---
    st.divider()
    col1, col2, col3 = st.columns([3, 4, 3])
    
    def render_player(d, align, color):
        if not d: return
        txt_align = "left" if align == "L" else "right"
        st.markdown(f"<div style='text-align:{txt_align};'><h3 style='color:{color}; margin:0;'>{d['navn']}</h3><p>{d['pos']} | {d['klub']}</p></div>", unsafe_allow_html=True)
        c_i, c_m = st.columns(2)
        with (c_i if align=="L" else c_m): vis_spiller_billede(d['img'])
        with (c_m if align=="L" else c_i):
            st.metric("Kampe", d['stats']['K'])
            st.metric("Mål", d['stats']['M'])

    with col1: render_player(data1, "L", "#df003b")
    with col3: render_player(data2, "R", "#0056a3")

    with col2:
        if data1 and data2:
            # Labels til visning
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggressiv.', 'Lederskab', 'Attitude', 'Udholdenh.']
            # Keys til data-hentning (matcher din CSV/Debug)
            keys = ['FART', 'TEKNIK', 'BESLUT', 'INTEL', 'AGGR', 'LEDER', 'ATT', 'UDH']
            
            def get_v(d):
                v = [d['r'].get(k, 0.1) for k in keys]
                return [float(x) for x in v] + [float(v[0])]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=get_v(data1), theta=labels+[labels[0]], fill='toself', name=data1['navn'], line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=get_v(data2), theta=labels+[labels[0]], fill='toself', name=data2['navn'], line_color='#0056a3'))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 6], tickvals=[1,2,3,4,5,6])),
                height=400,
                margin=dict(l=50,r=50,t=30,b=30),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

    if st.checkbox("Vis Debug Data"):
        st.write("Spiller 1 data:", data1['r'] if data1 else "Ingen")
        st.write("Spiller 2 data:", data2['r'] if data2 else "Ingen")
