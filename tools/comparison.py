import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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

def vis_side(df_spillere, playerstats, df_scout, player_seasons, season_filter):
    # 0. Standardiser kolonner på tværs af alle kilder
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

    # --- 2. FARVER & KONSTANTER ---
    hif_rod = "#df003b"
    gul_udlob = "#ffffcc"
    leje_gra = "#d3d3d3"
    rod_udlob = "#ffcccc"
    
     # --- TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">SCOUTING: SAMMENLIGNING</h3>
        </div>
    """, unsafe_allow_html=True)
    
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        match = combined_lookup[combined_lookup['NAVN'] == navn]
        if match.empty: 
            return None
        
        pid = str(match.iloc[0]['PLAYER_WYID'])

        # Standardværdier
        img_url = None
        klub = "Ukendt"
        pos = "Ukendt"

        # 1. Hent stamdata (Billede, klub, position)
        p_info = df_p[df_p['PLAYER_WYID'] == pid]
        if p_info.empty and df_spillere is not None:
            p_info = df_spillere[df_spillere['PLAYER_WYID'] == pid]

        if not p_info.empty:
            row = p_info.iloc[0]
            img_url = row.get('IMAGEDATAURL', None)
            klub = row.get('TEAMNAME', 'Ukendt')
            pos = map_position(row.get('ROLECODE3', row.get('POS', '')))
        else:
            # Tjek scouting data hvis stamdata mangler
            sc_info = df_s[df_s['PLAYER_WYID'] == pid]
            if not sc_info.empty:
                row_s = sc_info.iloc[-1]
                # TILFØJ DENNE LINJE:
                img_url = row_s.get('IMAGEDATAURL', None) 
                
                klub = row_s.get('KLUB', 'Scouting')
                pos = map_position(row_s.get('POSITION', ''))

        # 2. Hent Stats (Mål, Kampe, Minutter)
        stats = {'KAMPE': 0, 'MIN': 0, 'MÅL': 0}
        if playerstats is not None and not playerstats.empty:
            df_st = playerstats[playerstats['PLAYER_WYID'] == pid]
            if not df_st.empty:
                stats['KAMPE'] = int(df_st['MATCHES'].sum())
                stats['MIN'] = int(df_st['MINUTESONFIELD'].sum())
                stats['MÅL'] = int(df_st['GOALS'].sum())

        # 3. Hent Ratings fra scouting-ark
        tech = {k: 0 for k in ['FART', 'UDHOLDENHED', 'TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'ATTITUDE', 'LEDEREGENSKABER', 'AGGRESIVITET']}
        if not df_s.empty:
            sc_m = df_s[df_s['PLAYER_WYID'] == pid]
            if not sc_m.empty:
                n = sc_m.iloc[-1]
                for k in tech.keys():
                    try: 
                        val = n.get(k, 0)
                        tech[k] = float(str(val).replace(',', '.')) if pd.notna(val) else 0
                    except: 
                        tech[k] = 0
        
        return pid, klub, pos, stats, tech, img_url, navn

    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    # --- VISNING ---
    col1, col2, col3 = st.columns([3, 4, 3])
    
    def vis_profil(res, side, color):
        if not res: return
        pid, klub, pos, stats, tech, img_url, navn = res
        align = "left" if side == "venstre" else "right"
        
        st.markdown(f"<div style='text-align:{align};'><h3 style='color:{color}; margin-bottom:0;'>{navn}</h3>"
                    f"<p style='color:gray; margin-top:0;'>{pos} | {klub}</p></div>", unsafe_allow_html=True)
        
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
                v = [t['FART'], t['UDHOLDENHED'], t['TEKNIK'], t['SPILINTELLIGENS'], 
                     t['BESLUTSOMHED'], t['ATTITUDE'], t['LEDEREGENSKABER'], t['AGGRESIVITET']]
                v.append(v[0]) # Luk formen
                return v
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=get_radar_vals(res1[4]), theta=categories+[categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=get_radar_vals(res2[4]), theta=categories+[categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 6]),
                    gridshape='linear'  # HER skifter vi fra cirkel til 8-kant 🛑
                ),
                height=380, margin=dict(l=50, r=50, t=30, b=30), showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- TABS SEKTION ---
    st.divider()
    tab1, tab2, tab3, tab4 = st.tabs(["Generelt", "Offensivt", "Defensivt", "Scouting"])

    def vis_sammenligning_række(label, val1, val2, format_str="{:.1f}", højere_er_bedre=True):
        """Viser stats side-om-side med fremhævning af bedste værdi"""
        c1, c2, c3 = st.columns([2, 1, 2])
        
        # Håndter konvertering til tal
        try:
            v1_num = float(str(val1).replace(',', '.')) if pd.notna(val1) else 0.0
            v2_num = float(str(val2).replace(',', '.')) if pd.notna(val2) else 0.0
        except:
            v1_num, v2_num = 0.0, 0.0
        
        # Farve-logik
        v1_color = "black"
        v2_color = "black"
        
        if v1_num != v2_num:
            if højere_er_bedre:
                if v1_num > v2_num: v1_color = "#df003b" # Rød (Spiller 1's farve)
                else: v2_color = "#0056a3" # Blå (Spiller 2's farve)
            else:
                if v1_num < v2_num: v1_color = "#df003b"
                else: v2_color = "#0056a3"

        v1_txt = format_str.format(v1_num)
        v2_txt = format_str.format(v2_num)

        c1.markdown(f"<div style='text-align:right; font-weight:bold; color:{v1_color};'>{v1_txt}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='text-align:center; color:gray; font-size:0.85rem;'>{label}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='text-align:left; font-weight:bold; color:{v2_color};'>{v2_txt}</div>", unsafe_allow_html=True)

    def hent_spiller_data(pid):
        if playerstats is not None and not playerstats.empty:
            match = playerstats[playerstats['PLAYER_WYID'] == pid]
            if not match.empty:
                return match.iloc[0]
        return pd.Series()

    s1_data = hent_spiller_data(res1[0]) if res1 else pd.Series()
    s2_data = hent_spiller_data(res2[0]) if res2 else pd.Series()

    with tab1:
        st.write("### Overordnede tal")
        vis_sammenligning_række("Kampe", s1_data.get('MATCHES', 0), s2_data.get('MATCHES', 0), "{:.0f}")
        vis_sammenligning_række("Minutter", s1_data.get('MINUTESONFIELD', 0), s2_data.get('MINUTESONFIELD', 0), "{:,.0f}")
        vis_sammenligning_række("Gule kort", s1_data.get('YELLOWCARDS', 0), s2_data.get('YELLOWCARDS', 0), "{:.0f}", højere_er_bedre=False)

    with tab2:
        st.write("### Offensive stats")
        vis_sammenligning_række("Mål", s1_data.get('GOALS', 0), s2_data.get('GOALS', 0))
        vis_sammenligning_række("Assists", s1_data.get('ASSISTS', 0), s2_data.get('ASSISTS', 0))
        vis_sammenligning_række("Skud", s1_data.get('SHOTS', 0), s2_data.get('SHOTS', 0))
        vis_sammenligning_række("Driblinger %", s1_data.get('SUCCESSFUL_DRIBBLES_PRC', 0), s2_data.get('SUCCESSFUL_DRIBBLES_PRC', 0))

    with tab3:
        st.write("### Defensive stats")
        vis_sammenligning_række("Dueller vundet %", s1_data.get('DEFENSIVE_DUELS_WON_PRC', 0), s2_data.get('DEFENSIVE_DUELS_WON_PRC', 0))
        vis_sammenligning_række("Interceptions", s1_data.get('INTERCEPTIONS', 0), s2_data.get('INTERCEPTIONS', 0))
        vis_sammenligning_række("Boldtab", s1_data.get('LOSSES', 0), s2_data.get('LOSSES', 0), højere_er_bedre=False)

    with tab4:
        st.write("### Scouting data")
        if res1 and res2:
            sc1 = df_s[df_s['PLAYER_WYID'] == res1[0]]
            sc2 = df_s[df_s['PLAYER_WYID'] == res2[0]]
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**{res1[6]}**")
                note1 = sc1.iloc[-1].get('NOTER', 'Ingen noter fundet') if not sc1.empty else "Ingen data"
                st.info(note1)
            with c2:
                st.markdown(f"**{res2[6]}**")
                note2 = sc2.iloc[-1].get('NOTER', 'Ingen noter fundet') if not sc2.empty else "Ingen data"
                st.info(note2)
