import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Fast konfiguration
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
    # 1. Forbered Data
    df_p = df_spillere.copy() if df_spillere is not None else pd.DataFrame()
    if not df_p.empty:
        df_p.columns = [c.upper() for c in df_p.columns]
        df_p['PID_CLEAN'] = df_p['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        if 'NAVN' not in df_p.columns:
            df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
            df_p['NAVN'] = df_p['NAVN'].replace('', df_p.get('PLAYER_NAME', 'Ukendt'))

    try:
        # Læs CSV og behold originale kolonnenavne til mapping, men lav en upper-case version til opslag
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    except:
        df_s = pd.DataFrame()

    # Navneliste
    navne_trup = df_p['NAVN'].unique().tolist() if not df_p.empty else []
    navne_scout = df_s['Navn'].unique().tolist() if not df_s.empty else []
    navne_liste = sorted(list(set(navne_trup + navne_scout)))

    if not navne_liste:
        st.warning("⚠️ Ingen data fundet.")
        return

    # UI Selectors
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0, key="comp_s1")
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1), key="comp_s2")

    def hent_data(navn):
        pid = None
        if not df_p.empty and navn in df_p['NAVN'].values:
            pid = df_p[df_p['NAVN'] == navn].iloc[0]['PID_CLEAN']
        elif not df_s.empty and navn in df_s['Navn'].values:
            pid = df_s[df_s['Navn'] == navn].iloc[0]['PID_CLEAN']
        
        if not pid: return None

        # Stamdata
        img, klub, pos = None, "Ukendt", "Ukendt"
        if not df_p.empty:
            m = df_p[df_p['PID_CLEAN'] == pid]
            if not m.empty:
                img, klub = m.iloc[0].get('IMAGEDATAURL'), m.iloc[0].get('TEAMNAME', 'Hvidovre IF')
                pos = map_position(m.iloc[0].get('ROLECODE3', ''))

        # Stats
        stats = {'M': 0, 'K': 0}
        if career_df is not None and not career_df.empty:
            career_df.columns = [c.upper() for c in career_df.columns]
            career_df['PID_CLEAN'] = career_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
            c_m = career_df[(career_df['PID_CLEAN'] == pid) & (career_df['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            if not c_m.empty:
                stats = {'M': int(c_m.iloc[0].get('GOAL', 0)), 'K': int(c_m.iloc[0].get('APPEARANCES', 0))}

        # Ratings fra din CSV (Vi bruger de eksakte navne fra din fil)
        r = {k: 0.1 for k in ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']}
        if not df_s.empty:
            s_match = df_s[df_s['PID_CLEAN'] == pid]
            if not s_match.empty:
                # Vi sorterer efter Dato for at få den nyeste observation
                n = s_match.sort_values('Dato').iloc[-1]
                r = {
                    'Fart': n.get('Fart', 0.1),
                    'Teknik': n.get('Teknik', 0.1),
                    'Beslut': n.get('Beslutsomhed', 0.1),
                    'Intel': n.get('Spilintelligens', 0.1),
                    'Aggr': n.get('Aggresivitet', 0.1),
                    'Leder': n.get('Lederegenskaber', 0.1),
                    'Att': n.get('Attitude', 0.1),
                    'Udh': n.get('Udholdenhed', 0.1)
                }
        return {"navn": navn, "img": img, "klub": klub, "pos": pos, "stats": stats, "r": r}

    data1, data2 = hent_data(s1_navn), hent_data(s2_navn)

    # VISUALISERING
    st.divider()
    col1, col2, col3 = st.columns([3, 4, 3])

    def render_player(d, align, color):
        if not d: return
        txt_a = "left" if align == "L" else "right"
        st.markdown(f"<div style='text-align:{txt_a};'><h3 style='color:{color}; margin:0;'>{d['navn']}</h3><p>{d['pos']} | {d['klub']}</p></div>", unsafe_allow_html=True)
        c_i, c_m = st.columns(2)
        with (c_i if align=="L" else c_m): vis_spiller_billede(d['img'])
        with (c_m if align=="L" else c_i):
            st.metric("Kampe", d['stats']['K'])
            st.metric("Mål", d['stats']['M'])

    with col1: render_player(data1, "L", "#df003b")
    with col3: render_player(data2, "R", "#0056a3")

    with col2:
        if data1 and data2:
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggressivitet', 'Lederskab', 'Attitude', 'Udholdenhed']
            keys = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
            
            def get_v(d):
                v = [float(d['r'].get(k, 0.1)) for k in keys]
                return v + [v[0]]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=get_v(data1), theta=labels+[labels[0]], fill='toself', name=data1['navn'], line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=get_v(data2), theta=labels+[labels[0]], fill='toself', name=data2['navn'], line_color='#0056a3'))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 6], tickvals=[1,2,3,4,5,6])),
                height=420, margin=dict(l=60,r=60,t=20,b=20), showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
