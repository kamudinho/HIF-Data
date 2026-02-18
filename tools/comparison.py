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
    res = pos_map.get(s_code, "Ukendt")
    return res if res != "nan" else "Ukendt"

def vis_spiller_billede(pid, w=90):
    pid_clean = str(pid).split('.')[0].strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except:
        st.image(std, width=w)

def vis_side(spillere, player_events, df_scout):
    # 0. Standardiser kolonnenavne til UPPERCASE
    for d in [spillere, player_events, df_scout]:
        if d is not None: d.columns = [c.upper() for c in d.columns]

    # 1. Navneforberedelse
    df_p = spillere.copy() if spillere is not None else pd.DataFrame()
    if not df_p.empty and 'NAVN' not in df_p.columns:
        df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
    
    df_s = df_scout.copy() if df_scout is not None else pd.DataFrame()
    if not df_s.empty and 'ID' not in df_s.columns and 'PLAYER_WYID' in df_s.columns:
        df_s = df_s.rename(columns={'PLAYER_WYID': 'ID'})

    combined = pd.concat([
        df_p[['NAVN', 'PLAYER_WYID']].rename(columns={'PLAYER_WYID': 'ID'}) if not df_p.empty else pd.DataFrame(),
        df_s[['NAVN', 'ID']] if not df_s.empty else pd.DataFrame()
    ]).drop_duplicates(subset=['NAVN'])
    
    navne_liste = sorted(combined['NAVN'].unique())
    if not navne_liste:
        st.warning("Ingen data fundet.")
        return

    st.markdown("### ⚖️ Spillersammenligning")
    c_sel1, c_sel2 = st.columns(2)
    with c_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with c_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        match = combined[combined['NAVN'] == navn]
        pid = str(match.iloc[0]['ID']).split('.')[0].strip() if not match.empty else "0"
        
        p_data = df_p[df_p['NAVN'] == navn]
        klub = p_data.iloc[0].get('TEAMNAME', 'Ukendt') if not p_data.empty else "Eksternt emne"
        pos = map_position(p_data.iloc[0].get('POS', '')) if not p_data.empty else "Ukendt"

        stats = {'KAMPE': 0, 'MIN': 0, 'MÅL': 0, 'M90': 0.0}
        
        if player_events is not None and not player_events.empty:
            # Robust match på ID
            p_stats_all = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(pid, na=False)]
            
            if not p_stats_all.empty:
                # SIKKER SORTERING: Tjekker for mulige sæson-kolonnenavne
                season_cols = [c for c in ['SÆSON', 'SEASON', 'SEASON_NAME'] if c in p_stats_all.columns]
                if season_cols:
                    nyeste = p_stats_all.sort_values(season_cols[0], ascending=False)[season_cols[0]].iloc[0]
                    p_stats = p_stats_all[p_stats_all[season_cols[0]] == nyeste]
                else:
                    p_stats = p_stats_all # Fallback til al data hvis ingen sæson-kolonne findes

                # Find de rigtige stat-kolonner
                min_col = 'MINUTESTAGGED' if 'MINUTESTAGGED' in p_stats.columns else ('MINUTESPLAYED' if 'MINUTESPLAYED' in p_stats.columns else None)
                goal_col = 'GOALS' if 'GOALS' in p_stats.columns else None
                match_col = 'MATCHES' if 'MATCHES' in p_stats.columns else None

                t_min = p_stats[min_col].sum() if min_col else 0
                t_mål = p_stats[goal_col].sum() if goal_col else 0
                
                stats['KAMPE'] = p_stats[match_col].sum() if match_col else 0
                stats['MIN'] = t_min
                stats['MÅL'] = t_mål
                if t_min > 0:
                    stats['M90'] = round((t_mål / t_min) * 90, 2)

        # Scouting data
        tech = {k: 0 for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']}
        scout_txt = {'s': '-', 'u': '-', 'v': '-'}
        if not df_s.empty:
            s_match = df_s[df_s['NAVN'] == navn]
            if not s_match.empty:
                n = s_match.iloc[-1]
                if str(klub) == "nan" or klub == "Ukendt": klub = n.get('KLUB', 'Ukendt')
                for k in tech.keys():
                    try: tech[k] = float(str(n.get(k, 0)).replace(',', '.'))
                    except: tech[k] = 0
                scout_txt = {'s': n.get('STYRKER', '-'), 'u': n.get('UDVIKLING', '-'), 'v': n.get('VURDERING', '-')}

        return pid, klub, pos, stats, tech, scout_txt

    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    col1, col2, col3 = st.columns([3, 4, 3])

    def vis_profil(navn, res, side, color):
        pid, klub, pos, stats, _, _ = res
        align = "left" if side == "venstre" else "right"
        
        # MINDRE NAVNE (22px i stedet for 26-32px)
        st.markdown(f"""
            <div style='text-align:{align}; margin-bottom: 10px;'>
                <h3 style='color:{color}; margin:0; font-size:22px;'>{navn}</h3>
                <p style='color:gray; font-size:13px; margin:0;'>{pos} | {klub}</p>
            </div>
            """, unsafe_allow_html=True)
        
        c1, c2 = (st.columns([1, 2]) if side == "venstre" else st.columns([2, 1]))
        with (c1 if side == "venstre" else c2): vis_spiller_billede(pid)
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        m = st.columns(4)
        m[0].metric("KAMPE", int(stats['KAMPE']))
        m[1].metric("MIN.", int(stats['MIN']))
        m[2].metric("MÅL", int(stats['MÅL']))
        m[3].metric("M/90", stats['M90'])

    with col1: vis_profil(s1_navn, res1, "venstre", "#df003b")
    with col3: vis_profil(s2_navn, res2, "højre", "#0056a3")

    with col2:
        # 8-kant med din rækkefølge
        categories = ['Teknik', 'Udholdenhed', 'Fart', 'Aggressivitet', 'Lederevner', 'Attitude', 'Spil-int.', 'Beslutsomhed']
        def get_vals(t):
            keys = ['TEKNIK', 'UDHOLDENHED', 'FART', 'AGGRESIVITET', 'LEDEREGENSKABER', 'ATTITUDE', 'SPILINTELLIGENS', 'BESLUTSOMHED']
            v = [t.get(k, 0) for k in keys]
            v.append(v[0])
            return v

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=get_vals(res1[4]), theta=categories + [categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=get_vals(res2[4]), theta=categories + [categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])),
            showlegend=False, height=380, margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    # Tabs til noter i bunden... (som før)
