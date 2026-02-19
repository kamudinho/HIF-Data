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
    return pos_map.get(s_code, "Ukendt")

def vis_spiller_billede(pid, w=90):
    pid_clean = str(pid).split('.')[0].strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except:
        st.image(std, width=w)

# --- HOVEDFUNKTION ---
def vis_side(spillere, playerstats, df_scout, player_seasons, season_filter):
    # 0. Standardiser kolonner
    for d in [spillere, playerstats, df_scout, player_seasons]:
        if d is not None: 
            d.columns = [c.upper() for c in d.columns]

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

    st.markdown("### ⚖️ Spillersammenligning")

    c_sel1, c_sel2 = st.columns(2)
    with c_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with c_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        # Find spillerens ID i den kombinerede liste
        match = combined_lookup[combined_lookup['NAVN'] == navn]
        if match.empty: 
            return None
        
        try:
            pid = int(float(str(match.iloc[0]['PLAYER_WYID'])))
        except (ValueError, TypeError, IndexError): 
            return None

        # SIKKERHEDSTJEK: Find info i trup-data (df_p)
        p_info = df_p[df_p['NAVN'] == navn]
        
        # Hvis spilleren ikke findes i truppen, sætter vi standardværdier
        if not p_info.empty:
            klub = p_info.iloc[0].get('TEAMNAME', 'Ukendt Klub')
            pos_val = p_info.iloc[0].get('POS', '')
            pos = map_position(pos_val)
        else:
            # Her fanges fejlen: Hvis spilleren kun findes i scouting-data
            klub = "Scouting / Ekstern"
            pos = "Ukendt"

        s = {
            'GEN': {'KAMPE': 0, 'MIN': 0, 'START': 0},
            'OFF': {'MÅL': 0, 'ASSISTS': 0, 'xG': 0.0, 'SKUD': 0.0, 'KEYPASS': 0.0, 'DRIBBLES': 0.0, 'TOUCHBOX': 0.0},
            'DEF': {'DUEL_PCT': 0.0, 'AERIAL_PCT': 0.0, 'INTERCEPTIONS': 0.0, 'DEF_ACTIONS': 0.0, 'RECOVERIES': 0.0}
        }
        
        # --- Statistik indlæsning (Samme som før, men med flere checks) ---
        if player_seasons is not None and not player_seasons.empty:
            clean_season = season_filter.replace("=", "").replace("'", "").strip()
            temp_seasons = player_seasons.copy()
            temp_seasons['PLAYER_WYID'] = pd.to_numeric(temp_seasons['PLAYER_WYID'], errors='coerce')
            
            s_match = temp_seasons[(temp_seasons['PLAYER_WYID'] == pid) & (temp_seasons['SEASONNAME'].astype(str).str.strip() == clean_season)]
            
            if not s_match.empty and playerstats is not None:
                try:
                    target_season_id = int(float(str(s_match.iloc[0]['SEASON_WYID'])))
                    df = playerstats[(pd.to_numeric(playerstats['PLAYER_WYID'], errors='coerce') == pid) & 
                                     (pd.to_numeric(playerstats['SEASON_WYID'], errors='coerce') == target_season_id)]
                    
                    if not df.empty:
                        t_min = df['MINUTESTAGGED'].sum()
                        p90 = t_min / 90 if t_min > 0 else 0
                        s['GEN']['KAMPE'] = int(df['MATCHES'].sum())
                        s['GEN']['MIN'] = int(t_min)
                        s['GEN']['START'] = int(df['MATCHESINSTART'].sum())
                        s['OFF']['MÅL'] = int(df['GOALS'].sum())
                        s['OFF']['ASSISTS'] = int(df['ASSISTS'].sum())
                        s['OFF']['xG'] = round(float(df['XGSHOT'].sum() + df['XGASSIST'].sum()), 2)
                        
                        if p90 > 0:
                            s['OFF']['SKUD'] = round(float(df['SHOTS'].sum() / p90), 1)
                            s['OFF']['KEYPASS'] = round(float(df['KEYPASSES'].sum() / p90), 1)
                            s['OFF']['DRIBBLES'] = round(float(df['DRIBBLES'].sum() / p90), 1)
                            s['OFF']['TOUCHBOX'] = round(float(df['TOUCHINBOX'].sum() / p90), 1)
                            s['DEF']['INTERCEPTIONS'] = round(float(df['INTERCEPTIONS'].sum() / p90), 1)
                            s['DEF']['DEF_ACTIONS'] = round(float(df['DEFENSIVEACTIONS'].sum() / p90), 1)
                            s['DEF']['RECOVERIES'] = round(float(df['RECOVERIES'].sum() / p90), 1)
                        
                        if df['DUELS'].sum() > 0:
                            s['DEF']['DUEL_PCT'] = round((df['DUELSWON'].sum() / df['DUELS'].sum()) * 100, 1)
                        if df['AERIALDUELS'].sum() > 0:
                            s['DEF']['AERIAL_PCT'] = round((df['AERIALDUELSWON'].sum() / df['AERIALDUELS'].sum()) * 100, 1)
                except:
                    pass # Spring over hvis dataformater driller i de enkelte felter

        # --- Radar/Scouting data ---
        tech = {k: 0 for k in ['FART', 'UDHOLDENHED', 'TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'ATTITUDE', 'LEDEREGENSKABER', 'AGGRESIVITET']}
        scout_txt = {'s': '-', 'u': '-', 'v': '-'}
        
        if df_s is not None and not df_s.empty:
            sc_match = df_s[df_s['NAVN'] == navn]
            if not sc_match.empty:
                n = sc_match.iloc[-1]
                for k in tech.keys():
                    try:
                        val = str(n.get(k, 0)).replace(',', '.')
                        tech[k] = float(val) if val != 'None' else 0
                    except: tech[k] = 0
                scout_txt = {'s': n.get('STYRKER', '-'), 'u': n.get('UDVIKLING', '-'), 'v': n.get('VURDERING', '-')}

        return pid, klub, pos, s, tech, scout_txt

    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    # VISNING AF PROFILER
    col1, col2, col3 = st.columns([3, 4, 3])
    
    def vis_top(navn, res, side, color):
        if not res: return
        pid, klub, pos, s, _, _ = res
        align = "left" if side == "venstre" else "right"
        st.markdown(f"<div style='text-align:{align}; margin-bottom:10px;'><h3 style='color:{color}; margin:0;'>{navn}</h3><p style='color:gray; margin:0;'>{pos} | {klub}</p></div>", unsafe_allow_html=True)
        
        c1, c2 = (st.columns([1, 2]) if side == "venstre" else st.columns([2, 1]))
        with (c1 if side == "venstre" else c2): vis_spiller_billede(pid)
        
        st.markdown("<br>", unsafe_allow_html=True)
        # Metrics kasser som på Top 5 siden
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
            v.append(v[0]); return v
        
        fig = go.Figure()
        if res1: fig.add_trace(go.Scatterpolar(r=get_vals(res1[4]), theta=categories+[categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
        if res2: fig.add_trace(go.Scatterpolar(r=get_vals(res2[4]), theta=categories+[categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), height=380, margin=dict(l=50, r=50, t=30, b=30), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # DETALJERET TABEL-SAMMENLIGNING (Ensartet med Top 5 / Stats design)
    st.markdown("---")
    t_off, t_def = st.tabs(["🔥 OFFENSIVT (P90)", "🛡️ DEFENSIVT"])

    def vis_metric_row(label, val1, val2, suffix="", higher_is_better=True):
        c1, c2, c3 = st.columns([3, 2, 3])
        if val1 > val2:
            c1_color = "#28a745" if higher_is_better else "#dc3545"
            c3_color = "white"
        elif val2 > val1:
            c3_color = "#28a745" if higher_is_better else "#dc3545"
            c1_color = "white"
        else:
            c1_color = c3_color = "white"
        
        c1.markdown(f"<p style='text-align:right; color:{c1_color}; font-size:18px; font-weight:bold; margin:0;'>{val1}{suffix}</p>", unsafe_allow_html=True)
        c2.markdown(f"<p style='text-align:center; color:#888; margin:0;'>{label}</p>", unsafe_allow_html=True)
        c3.markdown(f"<p style='text-align:left; color:{c3_color}; font-size:18px; font-weight:bold; margin:0;'>{val2}{suffix}</p>", unsafe_allow_html=True)

    if res1 and res2:
        with t_off:
            st.markdown("<br>", unsafe_allow_html=True)
            vis_metric_row("xG Total", res1[3]['OFF']['xG'], res2[3]['OFF']['xG'])
            vis_metric_row("Skud", res1[3]['OFF']['SKUD'], res2[3]['OFF']['SKUD'])
            vis_metric_row("Key Passes", res1[3]['OFF']['KEYPASS'], res2[3]['OFF']['KEYPASS'])
            vis_metric_row("Driblinger", res1[3]['OFF']['DRIBBLES'], res2[3]['OFF']['DRIBBLES'])
            vis_metric_row("Touches i felt", res1[3]['OFF']['TOUCHBOX'], res2[3]['OFF']['TOUCHBOX'])
        with t_def:
            st.markdown("<br>", unsafe_allow_html=True)
            vis_metric_row("Duel vundet %", res1[3]['DEF']['DUEL_PCT'], res2[3]['DEF']['DUEL_PCT'], suffix="%")
            vis_metric_row("Aerial vundet %", res1[3]['DEF']['AERIAL_PCT'], res2[3]['DEF']['AERIAL_PCT'], suffix="%")
            vis_metric_row("Interceptions", res1[3]['DEF']['INTERCEPTIONS'], res2[3]['DEF']['INTERCEPTIONS'])
            vis_metric_row("Def. Aktioner", res1[3]['DEF']['DEF_ACTIONS'], res2[3]['DEF']['DEF_ACTIONS'])
            vis_metric_row("Erobringer", res1[3]['DEF']['RECOVERIES'], res2[3]['DEF']['RECOVERIES'])

    # SCOUTING TEKSTER
    st.markdown("---")
    sc1, sc2 = st.columns(2)
    for r, col, color in [(res1, sc1, "#df003b"), (res2, sc2, "#0056a3")]:
        if r:
            with col:
                st.markdown(f"<h4 style='color:{color}; text-align:center;'>Notater</h4>", unsafe_allow_html=True)
                tab_s, tab_u, tab_v = st.tabs(["Styrker", "Udvikling", "Vurdering"])
                tab_s.info(r[5]['s']); tab_u.warning(r[5]['u']); tab_v.success(r[5]['v'])
