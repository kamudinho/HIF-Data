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
        "10": "Offensiv Midt", "11": "Venstre Kant",
        "GKP": "Målmand", "DEF": "Forsvar", "MID": "Midtbane", "FWD": "Angreb"
    }
    s_code = str(pos_code).split('.')[0].upper()
    return pos_map.get(s_code, "Ukendt")

def vis_spiller_billede(pid, w=90):
    pid_clean = str(pid).split('.')[0].strip()
    # Undgå "M-" (manuelt oprettede spillere) i billed-URL
    if "M-" in pid_clean:
        std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
        st.image(std, width=w)
        return
        
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except:
        st.image(std, width=w)

# --- HOVEDFUNKTION ---
def vis_side(spillere, playerstats, df_scout, player_seasons, season_filter):
    # 0. Standardiser kolonner og ID'er
    for d in [spillere, playerstats, df_scout, player_seasons]:
        if d is not None: 
            d.columns = [c.upper() for c in d.columns]
            if 'PLAYER_WYID' in d.columns:
                d['PLAYER_WYID'] = d['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    # 1. Saml navne (Trup + Scouting)
    df_p = spillere.copy() if spillere is not None else pd.DataFrame()
    if not df_p.empty and 'NAVN' not in df_p.columns:
        df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
    
    df_s = df_scout.copy() if df_scout is not None else pd.DataFrame()
    
    p_lookup = df_p[['NAVN', 'PLAYER_WYID']].dropna() if not df_p.empty else pd.DataFrame()
    s_lookup = df_s[['NAVN', 'PLAYER_WYID']].dropna() if not df_s.empty else pd.DataFrame()
    
    combined_lookup = pd.concat([p_lookup, s_lookup]).drop_duplicates(subset=['NAVN'])
    navne_liste = sorted(combined_lookup['NAVN'].unique())

    if not navne_liste:
        st.warning("Ingen spillere fundet i systemet eller scouting-databasen.")
        return

    st.markdown("### Spillersammenligning")

    c_sel1, c_sel2 = st.columns(2)
    with c_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with c_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        match = combined_lookup[combined_lookup['NAVN'] == navn]
        if match.empty: return None
        pid = str(match.iloc[0]['PLAYER_WYID'])

        # Hent basis info
        p_info = df_p[df_p['PLAYER_WYID'] == pid]
        if not p_info.empty:
            klub = p_info.iloc[0].get('TEAMNAME', 'Ukendt Klub')
            pos = map_position(p_info.iloc[0].get('ROLECODE3', p_info.iloc[0].get('POS', '')))
        else:
            # Tjek scouting-filen hvis ikke i truppen
            sc_info = df_s[df_s['PLAYER_WYID'] == pid]
            klub = sc_info.iloc[-1].get('KLUB', 'Ekstern/Scouting') if not sc_info.empty else "Ukendt"
            pos = map_position(sc_info.iloc[-1].get('POSITION', '')) if not sc_info.empty else "Ukendt"

        s = {
            'GEN': {'KAMPE': 0, 'MIN': 0},
            'OFF': {'MÅL': 0, 'ASSISTS': 0, 'xG': 0.0, 'SKUD': 0.0, 'KEYPASS': 0.0, 'DRIBBLES': 0.0, 'TOUCHBOX': 0.0},
            'DEF': {'DUEL_PCT': 0.0, 'AERIAL_PCT': 0.0, 'INTERCEPTIONS': 0.0, 'RECOVERIES': 0.0}
        }
        
        # Hent stats fra Snowflake
        if playerstats is not None and not playerstats.empty:
            df = playerstats[playerstats['PLAYER_WYID'] == pid]
            if not df.empty:
                t_min = df['MINUTESONFIELD'].sum()
                p90 = t_min / 90 if t_min > 0 else 0
                s['GEN']['KAMPE'] = int(df['MATCHES'].sum())
                s['GEN']['MIN'] = int(t_min)
                s['OFF']['MÅL'] = int(df['GOALS'].sum())
                s['OFF']['ASSISTS'] = int(df['ASSISTS'].sum())
                if p90 > 0:
                    s['OFF']['xG'] = round(float(df.get('XGSHOT', 0).sum()), 2)
                    s['OFF']['SKUD'] = round(float(df.get('SHOTS', 0).sum() / p90), 1)
                    s['OFF']['DRIBBLES'] = round(float(df.get('DRIBBLES', 0).sum() / p90), 1)
                    s['DEF']['INTERCEPTIONS'] = round(float(df.get('INTERCEPTIONS', 0).sum() / p90), 1)
                    s['DEF']['RECOVERIES'] = round(float(df.get('RECOVERIES', 0).sum() / p90), 1)

        # Hent scouting-ratings (Radarchart)
        tech = {k: 0 for k in ['FART', 'UDHOLDENHED', 'TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'ATTITUDE', 'LEDEREGENSKABER', 'AGGRESIVITET']}
        scout_txt = {'s': '-', 'u': '-', 'v': '-'}
        if not df_s.empty:
            sc_match = df_s[df_s['PLAYER_WYID'] == pid]
            if not sc_match.empty:
                n = sc_match.iloc[-1]
                for k in tech.keys():
                    try: 
                        tech[k] = float(str(n.get(k, 0)).replace(',', '.'))
                    except: tech[k] = 0
                scout_txt = {'s': n.get('STYRKER', '-'), 'u': n.get('UDVIKLING', '-'), 'v': n.get('VURDERING', '-')}
        
        return pid, klub, pos, s, tech, scout_txt

    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    col1, col2, col3 = st.columns([3, 4, 3])
    
    def vis_top(navn, res, side, color):
        if not res: return
        pid, klub, pos, s, _, _ = res
        align = "left" if side == "venstre" else "right"
        st.markdown(f"<div style='text-align:{align}; margin-bottom:10px;'><h3 style='color:{color}; margin:0;'>{navn}</h3><p style='color:gray; margin:0;'>{pos} | {klub}</p></div>", unsafe_allow_html=True)
        c1, c2 = (st.columns([1, 2]) if side == "venstre" else st.columns([2, 1]))
        with (c1 if side == "venstre" else c2): vis_spiller_billede(pid)
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Kampe", s['GEN']['KAMPE'])
        m2.metric("Min", s['GEN']['MIN'])
        m3.metric("Mål", s['OFF']['MÅL'])

    with col1: vis_top(s1_navn, res1, "venstre", "#df003b")
    with col3: vis_top(s2_navn, res2, "højre", "#0056a3")

    with col2:
        categories = ['Fart', 'Udholdenhed', 'Teknik', 'Spil-int.', 'Beslutsomhed', 'Attitude', 'Lederevner', 'Aggressivitet']
        def get_vals(t):
            v = [t.get('FART',0), t.get('UDHOLDENHED',0), t.get('TEKNIK',0), t.get('SPILINTELLIGENS',0), 
                 t.get('BESLUTSOMHED',0), t.get('ATTITUDE',0), t.get('LEDEREGENSKABER',0), t.get('AGGRESIVITET',0)]
            v.append(v[0])
            return v
        
        fig = go.Figure()
        if res1: fig.add_trace(go.Scatterpolar(r=get_vals(res1[4]), theta=categories+[categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
        if res2: fig.add_trace(go.Scatterpolar(r=get_vals(res2[4]), theta=categories+[categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
        
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])),
            height=380, margin=dict(l=50, r=50, t=30, b=30), showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    t_off, t_def = st.tabs(["OFFENSIVT (P90)", "DEFENSIVT"])

    def vis_metric_row(label, val1, val2, suffix="", higher_is_better=True):
        # 1. Konvertering til tal for sammenligning
        try:
            v1 = float(val1)
            v2 = float(val2)
        except (ValueError, TypeError):
            v1 = v2 = 0.0

        # 2. Farve-logik (Ingen hvide tal)
        neutral_grey = "#888888"
        win_green = "#28a745"
        lose_red = "#dc3545"

        if v1 == v2:
            # Hvis de er ens (inkl. begge 0), så brug grå til begge
            color1 = color2 = neutral_grey
        elif v1 > v2:
            color1 = win_green if higher_is_better else lose_red
            color2 = lose_red if higher_is_better else win_green
        else: # v2 > v1
            color1 = lose_red if higher_is_better else win_green
            color2 = win_green if higher_is_better else lose_red

        # 3. HTML Layout
        c1, c2, c3 = st.columns([3, 2, 3])
        
        # Spiller 1
        c1.markdown(
            f"<div style='text-align:right; padding-right:20px;'>"
            f"<span style='color:{color1}; font-size:22px; font-weight:800;'>{val1}{suffix}</span>"
            f"</div>", 
            unsafe_allow_html=True
        )
        
        # Midter Label
        c2.markdown(
            f"<div style='text-align:center; background-color:#1a1c23; border-radius:4px; padding:4px; border: 1px solid #333;'>"
            f"<span style='color:#bbb; font-size:12px; font-weight:bold; text-transform:uppercase;'>{label}</span>"
            f"</div>", 
            unsafe_allow_html=True
        )
        
        # Spiller 2
        c3.markdown(
            f"<div style='text-align:left; padding-left:20px;'>"
            f"<span style='color:{color2}; font-size:22px; font-weight:800;'>{val2}{suffix}</span>"
            f"</div>", 
            unsafe_allow_html=True
        )
