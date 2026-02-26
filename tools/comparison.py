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
    if pd.isna(img_url) or str(img_url).strip() == "" or img_url is None:
        st.image(std, width=w)
    else:
        # Sikrer at vi ikke får URL'er med "nan" strenge
        if str(img_url).lower() == 'nan':
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

    st.markdown("### Spillersammenligning")

    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_info(navn):
        match = combined_lookup[combined_lookup['NAVN'] == navn]
        if match.empty: 
            return None
        
        pid = str(match.iloc[0]['PLAYER_WYID'])

        # 1. Tjek først i din lokale CSV (df_p)
        p_info = df_p[df_p['PLAYER_WYID'] == pid]
        
        # 2. Hvis den er tom, så tjek i Snowflake-data (df_spillere)
        if p_info.empty and df_spillere is not None:
            p_info = df_spillere[df_spillere['PLAYER_WYID'] == pid]

        # Nu kan vi begynde at udtrække informationen
        img_url = None
        klub = "Ukendt"
        pos = "Ukendt"

        if not p_info.empty:
            row = p_info.iloc[0]
            # HER kan vi skrive rækken ud for at fejlfinde:
            # st.write(f"Data fundet for {navn}:", row) 
            
            img_url = row.get('IMAGEDATAURL', None)
            klub = row.get('TEAMNAME', 'Ukendt')
            pos = map_position(row.get('ROLECODE3', row.get('POS', '')))
        else:
            # Hvis spilleren slet ikke er i p_info, tjekker vi scouting data
            sc_info = df_s[df_s['PLAYER_WYID'] == pid]
            if not sc_info.empty:
                row = sc_info.iloc[-1]
                klub = row.get('KLUB', 'Scouting')
                pos = map_position(row.get('POSITION', ''))
    
        else:
            sc_info = df_s[df_s['PLAYER_WYID'] == pid]
            klub = sc_info.iloc[-1].get('KLUB', 'Scouting') if not sc_info.empty else "Ukendt"
            pos = map_position(sc_info.iloc[-1].get('POSITION', '')) if not sc_info.empty else "Ukendt"

        # Stats (Mål, Kampe, Minutter)
        stats = {'KAMPE': 0, 'MIN': 0, 'MÅL': 0}
        if playerstats is not None and not playerstats.empty:
            df_st = playerstats[playerstats['PLAYER_WYID'] == pid]
            if not df_st.empty:
                stats['KAMPE'] = int(df_st['MATCHES'].sum())
                stats['MIN'] = int(df_st['MINUTESONFIELD'].sum())
                stats['MÅL'] = int(df_st['GOALS'].sum())

        # Ratings (De 8 kategorier)
        tech = {k: 0 for k in ['FART', 'UDHOLDENHED', 'TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'ATTITUDE', 'LEDEREGENSKABER', 'AGGRESIVITET']}
        if not df_s.empty:
            sc_m = df_s[df_s['PLAYER_WYID'] == pid]
            if not sc_m.empty:
                n = sc_m.iloc[-1]
                for k in tech.keys():
                    try: tech[k] = float(str(n.get(k, 0)).replace(',', '.'))
                    except: tech[k] = 0
        
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
            # Map kategorierne præcis til tech-nøglerne
            def get_radar_vals(t):
                v = [t['FART'], t['UDHOLDENHED'], t['TEKNIK'], t['SPILINTELLIGENS'], 
                     t['BESLUTSOMHED'], t['ATTITUDE'], t['LEDEREGENSKABER'], t['AGGRESIVITET']]
                v.append(v[0]) # Luk cirklen
                return v
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=get_radar_vals(res1[4]), theta=categories+[categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=get_radar_vals(res2[4]), theta=categories+[categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 6])),
                height=380, margin=dict(l=50, r=50, t=30, b=30), showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
