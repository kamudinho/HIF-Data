import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.season_show import SEASONNAME

# --- 1. HJÆLPEFUNKTIONER ---
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

# --- 2. HOVEDFUNKTION (Matcher din main.py: comp.vis_side(dp["players"], None, None, dp["career"], None)) ---
def vis_side(df_spillere, dummy1, dummy2, career_df, dummy3):
    # Vi ignorerer de 'None' værdier du sender fra main.py (dummy1, 2, 3)
    
    # 1. Standardiser trup-data (Fra din players.csv)
    df_p = df_spillere.copy() if df_spillere is not None else pd.DataFrame()
    if not df_p.empty:
        df_p.columns = [c.upper() for c in df_p.columns]
        if 'NAVN' not in df_p.columns:
            df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
    
    # 2. Hent scouting data (Vi læser den direkte her for at få de nyeste noter/ratings)
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s.columns = [c.upper().strip() for c in df_s.columns]
        df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0]
    except:
        df_s = pd.DataFrame()

    # 3. Byg navne-liste til selectbox
    all_names = []
    if not df_p.empty: all_names.extend(df_p['NAVN'].tolist())
    if not df_s.empty: all_names.extend(df_s['NAVN'].tolist())
    navne_liste = sorted(list(set([n for n in all_names if n and str(n) != 'nan'])))

    if not navne_liste:
        st.warning("Ingen spillere fundet i hverken truppen eller scouting databasen.")
        return

    # --- UI ---
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1))

    def hent_data(navn):
        # Find ID
        pid = None
        if not df_p.empty and navn in df_p['NAVN'].values:
            pid = str(df_p[df_p['NAVN'] == navn].iloc[0]['PLAYER_WYID']).split('.')[0]
        elif not df_s.empty and navn in df_s['NAVN'].values:
            pid = str(df_s[df_s['NAVN'] == navn].iloc[0]['PLAYER_WYID']).split('.')[0]
        
        if not pid: return None

        # Stamdata
        img, klub, pos = None, "Ukendt", "Ukendt"
        p_match = df_p[df_p['PLAYER_WYID'].astype(str).str.contains(pid)] if not df_p.empty else pd.DataFrame()
        if not p_match.empty:
            img = p_match.iloc[0].get('IMAGEDATAURL')
            klub = p_match.iloc[0].get('TEAMNAME', 'Hvidovre IF')
            pos = map_position(p_match.iloc[0].get('ROLECODE3', ''))
        
        # Stats fra Snowflake (career_df)
        stats = {'M': 0, 'K': 0, 'MIN': 0}
        if career_df is not None and not career_df.empty:
            career_df.columns = [c.upper() for c in career_df.columns]
            # Match på ID og Sæson
            c_match = career_df[
                (career_df['PLAYER_WYID'].astype(str).str.contains(pid)) & 
                (career_df['SEASONNAME'].astype(str).str.contains(SEASONNAME))
            ]
            if not c_match.empty:
                row = c_match.iloc[0]
                stats = {'M': row.get('GOAL', 0), 'K': row.get('APPEARANCES', 0), 'MIN': row.get('MINUTESPLAYED', 0)}

        # Ratings fra Scouting CSV
        r = {k: 0.0 for k in ['FART', 'TEKNIK', 'BESLUT', 'INTEL', 'AGGR', 'LEDER', 'ATT', 'UDH']}
        if not df_s.empty:
            s_match = df_s[df_s['PLAYER_WYID'].astype(str).str.contains(pid)]
            if not s_match.empty:
                n = s_match.iloc[-1]
                r = {
                    'FART': n.get('FART', 0), 'TEKNIK': n.get('TEKNIK', 0),
                    'BESLUT': n.get('BESLUTSOMHED', 0), 'INTEL': n.get('SPILINTELLIGENS', 0),
                    'AGGR': n.get('AGGRESIVITET', 0), 'LEDER': n.get('LEDEREGENSKABER', 0),
                    'ATT': n.get('ATTITUDE', 0), 'UDH': n.get('UDHOLDENHED', 0)
                }
        
        return {"navn": navn, "pid": pid, "img": img, "klub": klub, "pos": pos, "stats": stats, "r": r}

    d1 = hent_data(s1_navn)
    d2 = hent_data(s2_navn)

    # --- VISNING ---
    col1, col2, col3 = st.columns([3, 4, 3])
    
    def render_col(d, side, color):
        if not d: return
        align = "left" if side=="L" else "right"
        st.markdown(f"<div style='text-align:{align};'><h3 style='color:{color};'>{d['navn']}</h3><p>{d['pos']} | {d['klub']}</p></div>", unsafe_allow_html=True)
        c_i, c_m = st.columns(2)
        with (c_i if side=="L" else c_m): vis_spiller_billede(d['img'])
        with (c_m if side=="L" else c_i):
            st.metric("Mål", d['stats']['M'])
            st.metric("Kampe", d['stats']['K'])

    with col1: render_col(d1, "L", "#df003b")
    with col3: render_col(d2, "R", "#0056a3")

    with col2:
        if d1 and d2:
            labels = ['Fart', 'Teknik', 'Beslut.', 'Intell.', 'Aggres.', 'Leder', 'Attit.', 'Udhold.']
            def get_v(d): 
                v = [d['r']['FART'], d['r']['TEKNIK'], d['r']['BESLUT'], d['r']['INTEL'], d['r']['AGGR'], d['r']['LEDER'], d['r']['ATT'], d['r']['UDH']]
                return v + [v[0]]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=get_v(d1), theta=labels+[labels[0]], fill='toself', name=d1['navn'], line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=get_v(d2), theta=labels+[labels[0]], fill='toself', name=d2['navn'], line_color='#0056a3'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), height=350, margin=dict(l=40,r=40,t=20,b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
