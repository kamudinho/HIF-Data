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
    """Viser billede fra URL eller fallback hvis tom"""
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    if pd.isna(img_url) or str(img_url).strip() == "" or img_url is None:
        st.image(std, width=w)
    else:
        st.image(img_url, width=w)

# --- HOVEDFUNKTION ---
def vis_side(gh_players, playerstats, df_scout, player_seasons, season_filter):
    # 'gh_players' er ofte din GitHub-fil, 'sql_players' (fra din data_load) har IMAGEDATAURL
    # For at gøre det nemt, sikrer vi os at vi arbejder med de rigtige data
    
    # 0. Standardiser kolonner
    dfs = [gh_players, playerstats, df_scout]
    for d in dfs:
        if d is not None:
            d.columns = [c.upper() for c in d.columns]
            if 'PLAYER_WYID' in d.columns:
                d['PLAYER_WYID'] = d['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    # 1. Byg Lookup Tabel (Vi bruger NAVN som nøgle i selectbox)
    df_p = gh_players.copy() if gh_players is not None else pd.DataFrame()
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
        if match.empty: return None
        pid = str(match.iloc[0]['PLAYER_WYID'])

        # Hent info og BILLEDE-URL fra databasen
        p_info = df_p[df_p['PLAYER_WYID'] == pid]
        img_url = None
        
        if not p_info.empty:
            row = p_info.iloc[0]
            klub = row.get('TEAMNAME', 'Ukendt')
            pos = map_position(row.get('ROLECODE3', row.get('POS', '')))
            # HER HENTES DIN NYE KOLONNE
            img_url = row.get('IMAGEDATAURL', None)
        else:
            sc_info = df_s[df_s['PLAYER_WYID'] == pid]
            klub = sc_info.iloc[-1].get('KLUB', 'Scouting') if not sc_info.empty else "Ukendt"
            pos = map_position(sc_info.iloc[-1].get('POSITION', '')) if not sc_info.empty else "Ukendt"

        # Stats opsamling
        s = {'GEN': {'KAMPE': 0, 'MIN': 0}, 'OFF': {'MÅL': 0, 'xG': 0.0}, 'DEF': {'INT': 0.0}}
        if playerstats is not None and not playerstats.empty:
            df_st = playerstats[playerstats['PLAYER_WYID'] == pid]
            if not df_st.empty:
                s['GEN']['KAMPE'] = int(df_st['MATCHES'].sum())
                s['GEN']['MIN'] = int(df_st['MINUTESONFIELD'].sum())
                s['OFF']['MÅL'] = int(df_st['GOALS'].sum())
                s['OFF']['xG'] = round(float(df_st.get('XGSHOT', 0).sum()), 2)

        # Ratings til radar
        tech = {k: 0 for k in ['FART', 'TEKNIK', 'ATTITUDE', 'SPILINTELLIGENS', 'BESLUTSOMHED']}
        if not df_s.empty:
            sc_m = df_s[df_s['PLAYER_WYID'] == pid]
            if not sc_m.empty:
                for k in tech.keys():
                    try: tech[k] = float(str(sc_m.iloc[-1].get(k, 0)).replace(',', '.'))
                    except: tech[k] = 0
        
        # Vi returnerer nu: 0:ID, 1:Klub, 2:Pos, 3:Stats, 4:Tech, 5:Billede, 6:Navn
        return pid, klub, pos, s, tech, img_url, navn

    res1 = hent_info(s1_navn)
    res2 = hent_info(s2_navn)

    # --- UI LAYOUT ---
    col1, col2, col3 = st.columns([3, 4, 3])
    
    def vis_profil(res, side, color):
        if not res: return
        pid, klub, pos, s, tech, img_url, navn = res
        align = "left" if side == "venstre" else "right"
        
        # Overskrift med navn (ikke ID!)
        st.markdown(f"""
            <div style='text-align:{align};'>
                <h3 style='color:{color}; margin:0;'>{navn}</h3>
                <p style='color:gray; margin:0;'>{pos} | {klub}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Billede og hurtig-stats
        c_img, c_mtr = (st.columns([1, 1.5]) if side == "venstre" else st.columns([1.5, 1]))
        with (c_img if side == "venstre" else c_mtr):
            vis_spiller_billede(img_url)
        with (c_mtr if side == "venstre" else c_img):
            st.metric("Mål", s['OFF']['MÅL'])
            st.metric("Minutter", s['GEN']['MIN'])

    with col1: vis_profil(res1, "venstre", "#df003b")
    with col3: vis_profil(res2, "højre", "#0056a3")

    # Radar Chart i midten
    with col2:
        if res1 and res2:
            cat = ['Fart', 'Teknik', 'Attitude', 'Spil-int.', 'Beslutsomhed']
            def v(t): return [t[k.upper().replace('-','')] for k in cat] + [t['FART']]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=v(res1[4]), theta=cat+[cat[0]], fill='toself', name=s1_navn, line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=v(res2[4]), theta=cat+[cat[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), height=350, showlegend=False, margin=dict(l=40, r=40, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
