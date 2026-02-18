import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

# --- HJÆLPEFUNKTIONER ---
def map_position(pos_code):
    """Mapper talkoder til læsbare positioner."""
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    s_code = str(pos_code).split('.')[0]
    return pos_map.get(s_code, "Ukendt")

def vis_spiller_billede(pid, w=90):
    """Henter og viser spillerbillede fra Wyscout CDN."""
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
    # 0. Sørg for at alle kolonnenavne er UPPERCASE for stabilitet
    for d in [spillere, playerstats, df_scout, player_seasons]:
        if d is not None: 
            d.columns = [c.upper() for c in d.columns]

    # 1. Forberedelse af spillervalg fra truppen
    df_p = spillere.copy() if spillere is not None else pd.DataFrame()
    if not df_p.empty and 'NAVN' not in df_p.columns:
        df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
    
    navne_liste = sorted(df_p['NAVN'].unique()) if not df_p.empty else []

    if not navne_liste:
        st.warning("Ingen spillere fundet i truppen.")
        return

    # 2. UI: Spillersammenligning Header
    st.markdown("### ⚖️ Spillersammenligning")
    c_sel1, c_sel2 = st.columns(2)
    with c_sel1: 
        s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with c_sel2: 
        s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        # Find basis info i trup-data via PLAYER_WYID
        p_match = df_p[df_p['NAVN'] == navn]
        if p_match.empty: return None
        
        pid = int(float(str(p_match.iloc[0].get('PLAYER_WYID', 0))))
        klub = p_match.iloc[0].get('TEAMNAME', 'Hvidovre IF')
        pos = map_position(p_match.iloc[0].get('POS', ''))

        stats = {'KAMPE': 0, 'MIN': 0, 'MÅL': 0, 'M90': 0.0}
        
        # --- LOGIK: Kobling til Playerstats via Season ID ---
        if player_seasons is not None and not player_seasons.empty:
            # Rens filteret så det passer til tekst-match (f.eks. "2025/2026")
            clean_season = season_filter.replace("= '", "").replace("'", "").strip()
            
            # Find SEASON_WYID for spilleren i den valgte sæson
            s_match = player_seasons[
                (player_seasons['PLAYER_WYID'] == pid) & 
                (player_seasons['SEASONNAME'] == clean_season)
            ]
            
            if not s_match.empty and playerstats is not None:
                target_season_id = s_match.iloc[0]['SEASON_WYID']
                
                # Træk de specifikke stats fra playerstats-tabellen
                p_stats = playerstats[
                    (playerstats['PLAYER_WYID'] == pid) & 
                    (playerstats['SEASON_WYID'] == target_season_id)
                ]
                
                if not p_stats.empty:
                    min_col = 'MINUTESTAGGED' if 'MINUTESTAGGED' in p_stats.columns else 'MINUTESPLAYED'
                    t_min = p_stats[min_col].sum()
                    t_mål = p_stats['GOALS'].sum() if 'GOALS' in p_stats.columns else 0
                    
                    stats['KAMPE'] = p_stats['MATCHES'].sum() if 'MATCHES' in p_stats.columns else 0
                    stats['MIN'] = t_min
                    stats['MÅL'] = t_mål
                    if t_min > 0:
                        stats['M90'] = round((t_mål / t_min) * 90, 2)

        # Scouting data til Radarchart (fra df_scout)
        tech = {k: 0 for k in ['TEKNIK', 'UDHOLDENHED', 'FART', 'AGGRESIVITET', 'LEDEREGENSKABER', 'ATTITUDE', 'SPILINTELLIGENS', 'BESLUTSOMHED']}
        scout_txt = {'s': '-', 'u': '-', 'v': '-'}
        if df_scout is not None and not df_scout.empty:
            sc_match = df_scout[df_scout['NAVN'] == navn]
            if not sc_match.empty:
                n = sc_match.iloc[-1]
                for k in tech.keys():
                    try: 
                        tech[k] = float(str(n.get(k, 0)).replace(',', '.'))
                    except: 
                        tech[k] = 0
                scout_txt = {'s': n.get('STYRKER', '-'), 'u': n.get('UDVIKLING', '-'), 'v': n.get('VURDERING', '-')}

        return pid, klub, pos, stats, tech, scout_txt

    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    # 3. VISNING AF PROFILER
    col1, col2, col3 = st.columns([3, 4, 3])

    def vis_profil(navn, res, side, color):
        if not res: return
        pid, klub, pos, stats, _, _ = res
        align = "left" if side == "venstre" else "right"
        
        # Header med navn og position
        st.markdown(f"""
            <div style='text-align:{align}; margin-bottom: 5px;'>
                <h3 style='color:{color}; margin:0; font-size:22px;'>{navn}</h3>
                <p style='color:gray; font-size:13px; margin:0;'>{pos} | {klub}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Billede og Metrics
        c_img, c_stat = (st.columns([1, 2]) if side == "venstre" else st.columns([2, 1]))
        with (c_img if side == "venstre" else c_stat): 
            vis_spiller_billede(pid)
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        m = st.columns(4)
        m[0].metric("KAMPE", int(stats['KAMPE']))
        m[1].metric("MIN.", int(stats['MIN']))
        m[2].metric("MÅL", int(stats['MÅL']))
        m[3].metric("M/90", stats['M90'])

    with col1: vis_profil(s1_navn, res1, "venstre", "#df003b")
    with col3: vis_profil(s2_navn, res2, "højre", "#0056a3")

    # 4. RADAR CHART
    with col2:
        categories = ['Teknik', 'Udholdenhed', 'Fart', 'Aggressivitet', 'Lederevner', 'Attitude', 'Spil-int.', 'Beslutsomhed']
        
        def get_vals(t):
            keys = ['TEKNIK', 'UDHOLDENHED', 'FART', 'AGGRESIVITET', 'LEDEREGENSKABER', 'ATTITUDE', 'SPILINTELLIGENS', 'BESLUTSOMHED']
            v = [t.get(k, 0) for k in keys]
            v.append(v[0]) # Lukker 8-kanten
            return v

        fig = go.Figure()
        if res1:
            fig.add_trace(go.Scatterpolar(r=get_vals(res1[4]), theta=categories + [categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
        if res2:
            fig.add_trace(go.Scatterpolar(r=get_vals(res2[4]), theta=categories + [categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
        
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])),
            showlegend=False, height=380, margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    # 5. SCOUTING NOTER (TABS)
    st.divider()
    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        if res1:
            t1 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
            t1[0].info(res1[5]['s']); t1[1].warning(res1[5]['u']); t1[2].success(res1[5]['v'])
    with sc_col2:
        if res2:
            t2 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
            t2[0].info(res2[5]['s']); t2[1].warning(res2[5]['u']); t2[2].success(res2[5]['v'])
