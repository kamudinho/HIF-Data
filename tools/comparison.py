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

def vis_side(spillere, playerstats, df_scout):
    # 0. Standardiser kolonner
    for d in [spillere, playerstats, df_scout]:
        if d is not None: d.columns = [c.upper() for c in d.columns]

    # 1. Samle navneliste fra truppen (df_p)
    df_p = spillere.copy() if spillere is not None else pd.DataFrame()
    if not df_p.empty and 'NAVN' not in df_p.columns:
        df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
    
    navne_liste = sorted(df_p['NAVN'].unique()) if not df_p.empty else []

    if not navne_liste:
        st.warning("Ingen spillere fundet i truppen.")
        return

    st.markdown("### ⚖️ Spillersammenligning")
    c_sel1, c_sel2 = st.columns(2)
    with c_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with c_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        # Find basis info fra truptabellen
        p_match = df_p[df_p['NAVN'] == navn]
        pid = str(p_match.iloc[0].get('PLAYER_WYID', '0')).split('.')[0].strip()
        klub = p_match.iloc[0].get('TEAMNAME', 'Hvidovre IF')
        pos = map_position(p_match.iloc[0].get('POS', ''))

        stats = {'KAMPE': 0, 'MIN': 0, 'MÅL': 0, 'M90': 0.0}
        
        # --- PLAYERSTATS AGGREGERING (AKTUEL SÆSON) ---
        if playerstats is not None and not playerstats.empty:
            # Match på PLAYER_WYID
            p_ev = playerstats[playerstats['PLAYER_WYID'].astype(str).str.contains(pid, na=False)]
            
            if not p_ev.empty:
                # Find nyeste sæson for denne spiller
                season_col = 'SÆSON' if 'SÆSON' in p_ev.columns else 'SEASON'
                nyeste = p_ev.sort_values(season_col, ascending=False)[season_col].iloc[0]
                
                # Filtrér så vi kun har den aktuelle sæson
                aktuel_df = p_ev[p_ev[season_col] == nyeste]
                
                # Summér tallene (hvis spilleren har spillet i flere turneringer i samme sæson)
                min_col = 'MINUTESTAGGED' if 'MINUTESTAGGED' in aktuel_df.columns else 'MINUTESPLAYED'
                t_min = aktuel_df[min_col].sum()
                t_mål = aktuel_df['GOALS'].sum()
                
                stats['KAMPE'] = aktuel_df['MATCHES'].sum()
                stats['MIN'] = t_min
                stats['MÅL'] = t_mål
                if t_min > 0:
                    stats['M90'] = round((t_mål / t_min) * 90, 2)

        # Scouting data til Radarchart (Hentes fra df_scout)
        tech = {k: 0 for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']}
        scout_txt = {'s': '-', 'u': '-', 'v': '-'}
        if df_scout is not None and not df_scout.empty:
            s_match = df_scout[df_scout['NAVN'] == navn]
            if not s_match.empty:
                n = s_match.iloc[-1]
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
        
        st.markdown(f"""
            <div style='text-align:{align}; margin-bottom: 5px;'>
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
        # 8-kant rækkefølge
        categories = ['Fart', 'Udholdenhed', 'Teknik', 'Spil-int.', 'Beslutsomhed', 'Attitude', 'Lederevner', 'Aggressivitet']
        def get_vals(t):
            keys = ['FART', 'UDHOLDENHED', 'TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'ATTITUDE', 'LEDEREGENSKABER', 'AGGRESIVITET']
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
    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        t = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t[0].info(res1[5]['s']); t[1].warning(res1[5]['u']); t[2].success(res1[5]['v'])
    with sc_col2:
        t = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t[0].info(res2[5]['s']); t[1].warning(res2[5]['u']); t[2].success(res2[5]['v'])
