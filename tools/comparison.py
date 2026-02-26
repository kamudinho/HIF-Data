import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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

def vis_spiller_billede(img_url, w=110):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    if pd.isna(img_url) or img_url == "" or img_url is None:
        st.image(std, width=w)
    else:
        st.image(img_url, width=w)

# --- HOVEDFUNKTION ---
def vis_side(spillere, playerstats, df_scout, player_seasons, season_filter):
    # 0. Standardiser kolonner og ID'er
    for d in [spillere, playerstats, df_scout, player_seasons]:
        if d is not None: 
            d.columns = [c.upper() for c in d.columns]
            if 'PLAYER_WYID' in d.columns:
                d['PLAYER_WYID'] = d['PLAYER_WYID'].astype(str).split('.').str[0].str.strip()

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
        st.warning("Ingen spillere fundet.")
        return

    st.markdown("### Spillersammenligning")

    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        match = combined_lookup[combined_lookup['NAVN'] == navn]
        if match.empty: return None
        pid = str(match.iloc[0]['PLAYER_WYID'])

        p_info = df_p[df_p['PLAYER_WYID'] == pid]
        img_url = None
        
        if not p_info.empty:
            klub = p_info.iloc[0].get('TEAMNAME', 'Ukendt Klub')
            pos = map_position(p_info.iloc[0].get('ROLECODE3', p_info.iloc[0].get('POS', '')))
            img_url = p_info.iloc[0].get('IMAGEDATAURL', None)
        else:
            sc_info = df_s[df_s['PLAYER_WYID'] == pid]
            klub = sc_info.iloc[-1].get('KLUB', 'Ekstern/Scouting') if not sc_info.empty else "Ukendt"
            pos = map_position(sc_info.iloc[-1].get('POSITION', '')) if not sc_info.empty else "Ukendt"

        s = {
            'GEN': {'KAMPE': 0, 'MIN': 0},
            'OFF': {'MÅL': 0, 'xG': 0.0, 'SKUD': 0.0, 'DRIBBLES': 0.0},
            'DEF': {'INTERCEPTIONS': 0.0, 'RECOVERIES': 0.0}
        }
        
        if playerstats is not None and not playerstats.empty:
            df = playerstats[playerstats['PLAYER_WYID'] == pid]
            if not df.empty:
                t_min = df['MINUTESONFIELD'].sum()
                p90 = t_min / 90 if t_min > 0 else 0
                s['GEN']['KAMPE'] = int(df['MATCHES'].sum())
                s['GEN']['MIN'] = int(t_min)
                s['OFF']['MÅL'] = int(df['GOALS'].sum())
                s['OFF']['xG'] = round(float(df.get('XGSHOT', 0).sum()), 2)
                if p90 > 0:
                    s['OFF']['SKUD'] = round(float(df.get('SHOTS', 0).sum() / p90), 1)
                    s['OFF']['DRIBBLES'] = round(float(df.get('DRIBBLES', 0).sum() / p90), 1)
                    s['DEF']['INTERCEPTIONS'] = round(float(df.get('INTERCEPTIONS', 0).sum() / p90), 1)
                    s['DEF']['RECOVERIES'] = round(float(df.get('RECOVERIES', 0).sum() / p90), 1)

        tech = {k: 0 for k in ['FART', 'UDHOLDENHED', 'TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'ATTITUDE', 'LEDEREGENSKABER', 'AGGRESIVITET']}
        if not df_s.empty:
            sc_match = df_s[df_s['PLAYER_WYID'] == pid]
            if not sc_match.empty:
                n = sc_match.iloc[-1]
                for k in tech.keys():
                    try: tech[k] = float(str(n.get(k, 0)).replace(',', '.'))
                    except: tech[k] = 0
        
        # Returnerer nu også NAVN som res[6]
        return pid, klub, pos, s, tech, img_url, navn

    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    # --- VISNING ---
    col1, col2, col3 = st.columns([3, 4, 3])
    
    def vis_profil(res, side, color):
        if not res: return
        pid, klub, pos, s, tech, img_url, navn = res # Henter navn her
        align = "left" if side == "venstre" else "right"
        
        # Her bruger vi 'navn' variablen i stedet for ID'et
        st.markdown(f"<div style='text-align:{align};'><h3 style='color:{color}; margin-bottom:0;'>{navn}</h3>"
                    f"<p style='color:gray; margin-top:0;'>{pos}<br>{klub}</p></div>", unsafe_allow_html=True)
        
        c_img, c_txt = (st.columns([1, 1.5]) if side == "venstre" else st.columns([1.5, 1]))
        with (c_img if side == "venstre" else c_txt):
            vis_spiller_billede(img_url)
        
        st.write(" ")
        m1, m2 = st.columns(2)
        m1.metric("Kampe", s['GEN']['KAMPE'])
        m2.metric("Minutter", s['GEN']['MIN'])

    with col1: vis_profil(res1, "venstre", "#df003b")
    with col3: vis_profil(res2, "højre", "#0056a3")

    with col2:
        if res1 and res2:
            # Radar chart logik her...
            categories = ['Fart', 'Udholdenhed', 'Teknik', 'Spil-int.', 'Beslutsomhed', 'Attitude', 'Lederevner', 'Aggressivitet']
            def get_vals(t):
                v = [t.get('FART',0), t.get('UDHOLDENHED',0), t.get('TEKNIK',0), t.get('SPILINTELLIGENS',0), 
                     t.get('BESLUTSOMHED',0), t.get('ATTITUDE',0), t.get('LEDEREGENSKABER',0), t.get('AGGRESIVITET',0)]
                v.append(v[0])
                return v
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=get_vals(res1[4]), theta=categories+[categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=get_vals(res2[4]), theta=categories+[categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), height=350, margin=dict(l=40, r=40, t=20, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # ... fortsæt med tabs og rækker
    
    def vis_metric_row(label, val1, val2, suffix="", higher_is_better=True):
        # 1. Sikr at vi har tal til sammenligning og strenge til visning
        try:
            v1 = float(val1) if val1 is not None else 0.0
            v2 = float(val2) if val2 is not None else 0.0
        except:
            v1 = v2 = 0.0
            
        display_v1 = str(val1) if val1 is not None else "0"
        display_v2 = str(val2) if val2 is not None else "0"

        # 2. Farve-logik (Grøn = vinder, Rød = taber, Grå = ens)
        neutral_grey = "#888888"
        win_green = "#28a745"
        lose_red = "#dc3545"

        if v1 == v2:
            color1 = color2 = neutral_grey
        elif v1 > v2:
            color1 = win_green if higher_is_better else lose_red
            color2 = lose_red if higher_is_better else win_green
        else:
            color1 = lose_red if higher_is_better else win_green
            color2 = win_green if higher_is_better else lose_red

        # 3. Layout med columns
        c1, c2, c3 = st.columns([3, 2, 3])
        
        with c1:
            st.markdown(f"<p style='text-align:right; color:{color1}; font-size:22px; font-weight:800; margin:0;'>{display_v1}{suffix}</p>", unsafe_allow_html=True)
        
        with c2:
            st.markdown(f"<div style='text-align:center; background-color:#ffffff; border-radius:4px; border:1px solid #888888;'><span style='color:#000000; font-size:12px; font-weight:bold; text-transform:uppercase;'>{label}</span></div>", unsafe_allow_html=True)
        
        with c3:
            st.markdown(f"<p style='text-align:left; color:{color2}; font-size:22px; font-weight:800; margin:0;'>{display_v2}{suffix}</p>", unsafe_allow_html=True)

    # --- TJEK OM DATA FINDES FØR VISNING ---
    if res1 and res2:
        with t_off:
            st.write(" ") # Skaber lidt luft
            # Hent tallene specifikt fra din dictionary struktur: res[3]['OFF']...
            vis_metric_row("Mål", res1[3]['OFF']['MÅL'], res2[3]['OFF']['MÅL'])
            vis_metric_row("xG Total", res1[3]['OFF']['xG'], res2[3]['OFF']['xG'])
            vis_metric_row("Skud", res1[3]['OFF']['SKUD'], res2[3]['OFF']['SKUD'])
            vis_metric_row("Driblinger", res1[3]['OFF']['DRIBBLES'], res2[3]['OFF']['DRIBBLES'])
        
        with t_def:
            st.write(" ")
            vis_metric_row("Interceptions", res1[3]['DEF']['INTERCEPTIONS'], res2[3]['DEF']['INTERCEPTIONS'])
            vis_metric_row("Erobringer", res1[3]['DEF']['RECOVERIES'], res2[3]['DEF']['RECOVERIES'])
    else:
        st.info("Vælg to spillere for at se sammenligningen.")
