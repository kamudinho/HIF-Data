import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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
    if pd.isna(img_url) or str(img_url).strip() == "" or img_url is None or str(img_url).lower() == 'nan':
        st.image(std, width=w)
    else:
        st.image(img_url, width=w)

def hent_spiller_data(pid, stats_df):
    if stats_df is not None and not stats_df.empty:
        pid_s = str(pid).split('.')[0].strip()
        
        # --- FIX STARTER HER ---
        # Tjek hvilken sæson-kolonne der rent faktisk findes i dit datasæt
        if 'SEASONNAME' in stats_df.columns:
            s_col = 'SEASONNAME'
        elif 'SEASON' in stats_df.columns:
            s_col = 'SEASON'
        else:
            # Hvis ingen af delene findes, returner den nyeste række for spilleren
            return stats_df[stats_df['PLAYER_WYID'].astype(str).str.contains(pid_s)].iloc[-1] if not stats_df[stats_df['PLAYER_WYID'].astype(str).str.contains(pid_s)].empty else pd.Series()
        # --- FIX SLUTTER HER ---
        
        match = stats_df[
            (stats_df['PLAYER_WYID'].astype(str).str.contains(pid_s)) & 
            (stats_df[s_col].astype(str).str.contains(SEASONNAME))
        ]
        
        if not match.empty:
            return match.iloc[0]
            
    return pd.Series()
            
        # Fallback: Tag nyeste række hvis den valgte sæson ikke findes
        backup = stats_df[stats_df['PLAYER_WYID'].astype(str).str.contains(pid_s)]
        if not backup.empty:
            return backup.sort_values(s_col).iloc[-1]
            
    return pd.Series()

# --- 2. HOVEDFUNKTION FOR SIDEN ---
def vis_side(df_spillere, playerstats, df_scout, player_seasons, season_filter):
    # 0. Standardiser kolonner
    for d in [df_spillere, playerstats, df_scout]:
        if d is not None:
            d.columns = [c.upper() for c in d.columns]
            if 'PLAYER_WYID' in d.columns:
                d['PLAYER_WYID'] = d['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    # 1. Byg navne-lookup
    df_p = df_spillere.copy() if df_spillere is not None else pd.DataFrame()
    if not df_p.empty and 'NAVN' not in df_p.columns:
        df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
    
    df_s = df_scout.copy() if df_scout is not None else pd.DataFrame()
    
    combined_lookup = pd.concat([
        df_p[['NAVN', 'PLAYER_WYID']].dropna(),
        df_s[['NAVN', 'PLAYER_WYID']].dropna()
    ]).drop_duplicates(subset=['NAVN'])
    
    navne_liste = sorted(combined_lookup['NAVN'].unique())

    if not navne_liste:
        st.warning("Ingen spillere fundet.")
        return

    # --- BRANDING & VALG ---
    hif_rod = "#df003b"
    st.markdown(f'<div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;"><h3 style="color:white; margin:0; text-align:center;">SCOUTING: SAMMENLIGNING</h3></div>', unsafe_allow_html=True)
    
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        match = combined_lookup[combined_lookup['NAVN'] == navn]
        if match.empty: return None
        pid = str(match.iloc[0]['PLAYER_WYID'])

        # Hent stamdata fra enten spillerliste eller scouting
        p_info = df_p[df_p['PLAYER_WYID'] == pid]
        if not p_info.empty:
            row = p_info.iloc[0]
            img_url = row.get('IMAGEDATAURL')
            klub = row.get('TEAMNAME', 'Ukendt')
            pos = map_position(row.get('ROLECODE3', row.get('POS', '')))
        else:
            sc_info = df_s[df_s['PLAYER_WYID'] == pid]
            row_s = sc_info.iloc[-1] if not sc_info.empty else {}
            img_url = row_s.get('IMAGEDATAURL')
            klub = row_s.get('KLUB', 'Scouting')
            pos = map_position(row_s.get('POSITION', ''))

        # Hent stats via hjælpefunktion
        s_data = hent_spiller_data(pid, playerstats)
        stats = {
            'KAMPE': int(s_data.get('MATCHES', 0)),
            'MIN': int(s_data.get('MINUTESONFIELD', 0)),
            'MÅL': int(s_data.get('GOALS', 0))
        }

        # Ratings
        tech = {k: 0 for k in ['FART', 'UDHOLDENHED', 'TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'ATTITUDE', 'LEDEREGENSKABER', 'AGGRESIVITET']}
        sc_m = df_s[df_s['PLAYER_WYID'] == pid]
        if not sc_m.empty:
            n = sc_m.iloc[-1]
            for k in tech.keys():
                val = n.get(k, 0)
                tech[k] = float(str(val).replace(',', '.')) if pd.notna(val) else 0
        
        return pid, klub, pos, stats, tech, img_url, navn

    # Hent profil-data
    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    # --- VISNING AF PROFILER ---
    col1, col2, col3 = st.columns([3, 4, 3])
    
    def vis_profil(res, side, color):
        if not res: return
        pid, klub, pos, stats, tech, img_url, navn = res
        align = "left" if side == "venstre" else "right"
        st.markdown(f"<div style='text-align:{align};'><h3 style='color:{color}; margin-bottom:0;'>{navn}</h3><p style='color:gray; margin-top:0;'>{pos} | {klub}</p></div>", unsafe_allow_html=True)
        
        c_img, c_mtr = (st.columns([1, 1.2]) if side == "venstre" else st.columns([1.2, 1]))
        with (c_img if side == "venstre" else c_mtr):
            vis_spiller_billede(img_url)
        with (c_mtr if side == "venstre" else c_img):
            st.metric("Mål", stats['MÅL'])
            st.metric("Kampe", stats['KAMPE'])

    with col1: vis_profil(res1, "venstre", "#df003b")
    with col3: vis_profil(res2, "højre", "#0056a3")

    with col2:
        if res1 and res2:
            categories = ['Fart', 'Udholdenhed', 'Teknik', 'Spil-int.', 'Beslut.', 'Attitude', 'Leder', 'Aggres.']
            def get_radar_vals(t):
                v = [t['FART'], t['UDHOLDENHED'], t['TEKNIK'], t['SPILINTELLIGENS'], t['BESLUTSOMHED'], t['ATTITUDE'], t['LEDEREGENSKABER'], t['AGGRESIVITET']]
                v.append(v[0])
                return v
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=get_radar_vals(res1[4]), theta=categories+[categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=get_radar_vals(res2[4]), theta=categories+[categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6]), gridshape='linear'), height=380, margin=dict(l=50, r=50, t=30, b=30), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # --- TABS SEKTION ---
    st.divider()
    tab1, tab2, tab3, tab4 = st.tabs(["Generelt", "Offensivt", "Defensivt", "Scouting"])

    # Hjælpefunktion til rækker
    def vis_sammenligning_række(label, val1, val2, format_str="{:.1f}", højere_er_bedre=True):
        c1, c2, c3 = st.columns([2, 1, 2])
        v1 = float(str(val1).replace(',', '.')) if pd.notna(val1) else 0.0
        v2 = float(str(val2).replace(',', '.')) if pd.notna(val2) else 0.0
        
        v1_color = "#df003b" if (v1 > v2 if højere_er_bedre else v1 < v2) else "black"
        v2_color = "#0056a3" if (v2 > v1 if højere_er_bedre else v2 < v1) else "black"

        c1.markdown(f"<div style='text-align:right; font-weight:bold; color:{v1_color};'>{format_str.format(v1)}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='text-align:center; color:gray; font-size:0.85rem;'>{label}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='text-align:left; font-weight:bold; color:{v2_color};'>{format_str.format(v2)}</div>", unsafe_allow_html=True)

    # Hent data til faner
    s1_tab_data = hent_spiller_data(res1[0], playerstats) if res1 else pd.Series()
    s2_tab_data = hent_spiller_data(res2[0], playerstats) if res2 else pd.Series()

    with tab1:
        st.write("### Overordnede tal")
        vis_sammenligning_række("Kampe", s1_tab_data.get('MATCHES', 0), s2_tab_data.get('MATCHES', 0), "{:.0f}")
        vis_sammenligning_række("Minutter", s1_tab_data.get('MINUTESONFIELD', 0), s2_tab_data.get('MINUTESONFIELD', 0), "{:,.0f}")
        vis_sammenligning_række("Gule kort", s1_tab_data.get('YELLOWCARDS', 0), s2_tab_data.get('YELLOWCARDS', 0), "{:.0f}", højere_er_bedre=False)

    with tab2:
        st.write("### Offensive stats")
        vis_sammenligning_række("Mål", s1_tab_data.get('GOALS', 0), s2_tab_data.get('GOALS', 0))
        vis_sammenligning_række("Assists", s1_tab_data.get('ASSISTS', 0), s2_tab_data.get('ASSISTS', 0))
        vis_sammenligning_række("Skud", s1_tab_data.get('SHOTS', 0), s2_tab_data.get('SHOTS', 0))
        vis_sammenligning_række("Driblinger %", s1_tab_data.get('SUCCESSFUL_DRIBBLES_PRC', 0), s2_tab_data.get('SUCCESSFUL_DRIBBLES_PRC', 0))

    with tab3:
        st.write("### Defensive stats")
        vis_sammenligning_række("Dueller vundet %", s1_tab_data.get('DEFENSIVE_DUELS_WON_PRC', 0), s2_tab_data.get('DEFENSIVE_DUELS_WON_PRC', 0))
        vis_sammenligning_række("Interceptions", s1_tab_data.get('INTERCEPTIONS', 0), s2_tab_data.get('INTERCEPTIONS', 0))
        vis_sammenligning_række("Boldtab", s1_tab_data.get('LOSSES', 0), s2_tab_data.get('LOSSES', 0), højere_er_bedre=False)

    with tab4:
        st.write("### Scouting noter")
        if res1 and res2:
            c1, c2 = st.columns(2)
            with c1:
                st.info(df_s[df_s['PLAYER_WYID'] == res1[0]].iloc[-1].get('NOTER', 'Ingen noter')) if not df_s[df_s['PLAYER_WYID'] == res1[0]].empty else st.write("Ingen data")
            with c2:
                st.info(df_s[df_s['PLAYER_WYID'] == res2[0]].iloc[-1].get('NOTER', 'Ingen noter')) if not df_s[df_s['PLAYER_WYID'] == res2[0]].empty else st.write("Ingen data")
