import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

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

def vis_spiller_billede(img_url, pid, w=150):
    """Henter billede fra URL, genererer det fra PID eller bruger standard silhuet"""
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    
    # 1. Rens inputs så vi kan tjekke dem ordentligt
    img_clean = str(img_url).strip() if pd.notna(img_url) else ""
    pid_clean = str(pid).split('.')[0].strip() if pd.notna(pid) else ""
    
    # Liste over værdier vi betragter som "tomme/ugyldige"
    ugyldige = ["", "0", "0.0", "nan", "none", "undefined"]
    
    # LOGIK-KÆDE:
    if img_clean and img_clean.lower() not in ugyldige:
        url = img_clean
    elif pid_clean and pid_clean.lower() not in ugyldige:
        url = f"https://cdn5.wyscout.com/photos/players/public/{pid_clean}.png"
    else:
        url = std
        
    st.image(url, width=w)

def vis_side(df_spillere, d1, d2, career_df, d3):
    # --- 1. DATA SETUP ---
    df_p = df_spillere.copy() if df_spillere is not None else pd.DataFrame()
    if not df_p.empty:
        df_p.columns = [c.upper() for c in df_p.columns]
        df_p['PID_CLEAN'] = df_p['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Byg billed_map fra d3 (SQL)
    billed_map = {}
    if d3 is not None and not d3.empty:
        for _, row in d3.iterrows():
            pid_tmp = str(row.get('PLAYER_WYID', '')).split('.')[0].strip()
            url_tmp = row.get('IMAGEDATAURL')
            # SIKRING: Vi gemmer kun URL'en hvis den ikke er "0" eller tom
            if pid_tmp and pd.notna(url_tmp) and str(url_tmp).strip() not in ["0", "0.0", "nan", ""]:
                billed_map[pid_tmp] = str(url_tmp).strip()

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    except:
        df_s = pd.DataFrame()

    # Samlet navneliste
    navne_p = df_p['NAVN'].tolist() if 'NAVN' in df_p.columns else []
    navne_s = df_s['Navn'].tolist() if 'Navn' in df_s.columns else []
    navne_liste = sorted(list(set(navne_p + navne_s)))

    # --- 2. SELECTORS ---
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0, key="comp_s1")
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1), key="comp_s2")

    def hent_alle_data(navn):
        pid = None
        if not df_p.empty and 'NAVN' in df_p.columns and navn in df_p['NAVN'].values:
            pid = df_p[df_p['NAVN'] == navn].iloc[0]['PID_CLEAN']
        elif not df_s.empty and 'Navn' in df_s.columns and navn in df_s['Navn'].values:
            pid = df_s[df_s['Navn'] == navn].iloc[0]['PID_CLEAN']
        
        if not pid: return None

        res = {"navn": navn, "pid": pid, "img": None, "klub": "Ukendt", "pos": "Ukendt", "scout": {}, "stats": {}}
        
        # Billede-opslag i vores rensede map
        res["img"] = billed_map.get(str(pid))

        # Stamdata fra trup
        if not df_p.empty:
            m = df_p[df_p['PID_CLEAN'] == pid]
            if not m.empty:
                if not res["img"]:
                    img_trup = m.iloc[0].get('IMAGEDATAURL')
                    if pd.notna(img_trup) and str(img_trup).strip() not in ["0", "0.0", "nan", ""]:
                        res["img"] = str(img_trup).strip()
                res["klub"] = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')
                res["pos"] = map_position(m.iloc[0].get('ROLECODE3', ''))

        # Karriere Statistik
        stats = {"Kampe": 0, "Mål": 0, "Assist": 0, "Min": 0, "Gule": 0}
        if career_df is not None and not career_df.empty:
            cdf = career_df.copy()
            cdf.columns = [c.upper() for c in cdf.columns]
            cdf['PID_CLEAN'] = cdf['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
            c_m = cdf[(cdf['PID_CLEAN'] == pid) & (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            if not c_m.empty:
                stats = {
                    "Kampe": int(c_m.iloc[0].get('MATCHES', c_m.iloc[0].get('APPEARANCES', 0))),
                    "Mål": int(c_m.iloc[0].get('GOALS', c_m.iloc[0].get('GOAL', 0))),
                    "Assist": int(c_m.iloc[0].get('ASSIST', 0)),
                    "Min": int(c_m.iloc[0].get('MINUTES', c_m.iloc[0].get('MINUTESPLAYED', 0))),
                    "Gule": int(c_m.iloc[0].get('YELLOWCARD', c_m.iloc[0].get('YELLOWCARDS', 0)))
                }
        res["stats"] = stats

        # Scouting data
        if not df_s.empty:
            s_match = df_s[df_s['PID_CLEAN'] == pid].sort_values('Dato').iloc[-1:]
            if not s_match.empty:
                n = s_match.iloc[0]
                res["scout"] = {k: n.get(k, '-') for k in ['Styrker', 'Vurdering', 'Potentiale', 'Status']}
                res["r"] = {
                    'Fart': n.get('Fart', 0.1), 'Teknik': n.get('Teknik', 0.1),
                    'Beslut': n.get('Beslutsomhed', 0.1), 'Intel': n.get('Spilintelligens', 0.1),
                    'Aggr': n.get('Aggresivitet', 0.1), 'Leder': n.get('Lederegenskaber', 0.1),
                    'Att': n.get('Attitude', 0.1), 'Udh': n.get('Udholdenhed', 0.1)
                }
        return res

    p1, p2 = hent_alle_data(s1_navn), hent_alle_data(s2_navn)

    # --- 3. VISNING ---
    st.divider()
    c_img1, c_radar, c_img2 = st.columns([2, 4, 2])
    
    if p1:
        with c_img1:
            vis_spiller_billede(p1["img"], p1["pid"])
            st.subheader(p1["navn"])
            st.caption(f"{p1['pos']} | {p1['klub']}")
    
    if p2:
        with c_img2:
            st.markdown("<div style='text-align:right;'>", unsafe_allow_html=True)
            vis_spiller_billede(p2["img"], p2["pid"])
            st.subheader(p2["navn"])
            st.caption(f"{p2['pos']} | {p2['klub']}")
            st.markdown("</div>", unsafe_allow_html=True)

    with c_radar:
        if p1 and p2 and "r" in p1 and "r" in p2:
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
            keys = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=[p1['r'][k] for k in keys]+[p1['r'][keys[0]]], theta=labels+[labels[0]], fill='toself', name=p1['navn'], line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=[p2['r'][k] for k in keys]+[p2['r'][keys[0]]], theta=labels+[labels[0]], fill='toself', name=p2['navn'], line_color='#0056a3'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), height=350, margin=dict(l=40,r=40,t=20,b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    sc1, sc2 = st.columns(2)
    for i, p in enumerate([p1, p2]):
        with (sc1 if i==0 else sc2):
            if p:
                st.markdown("### 📊 Sæson Statistik")
                st.table(pd.DataFrame([p["stats"]], index=["Værdi"]).T)
                st.markdown("### 📝 Scoutens Noter")
                st.info(f"**Styrker:** {p['scout'].get('Styrker')}\n\n**Vurdering:** {p['scout'].get('Vurdering')}")
