import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

# --- HJÆLPEFUNKTIONER (Identiske med din profil-fil) ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def map_position(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    return pos_map.get(rens_id(pos_code), "Ukendt")

def vis_spiller_billede(img_url, pid, w=150):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    img_clean = str(img_url).strip() if pd.notna(img_url) else ""
    pid_clean = rens_id(pid)
    
    ugyldige = ["", "0", "0.0", "nan", "none", "undefined"]
    
    if img_clean and img_clean.lower() not in ugyldige:
        url = img_clean
    elif pid_clean and pid_clean not in ugyldige:
        url = f"https://cdn5.wyscout.com/photos/players/public/{pid_clean}.png"
    else:
        url = std
    st.image(url, width=w)

# --- HOVEDFUNKTION ---
def vis_side(df_spillere, d1, d2, career_df, d3):
    # 1. Hent Scouting DB (Kilden til alle spillere der skal vises)
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except:
        st.error("Kunne ikke læse scouting_db.csv")
        return

    # 2. Byg billed-opslag fra Snowflake (d3), præcis som i din profil-fil
    billed_map = {}
    if d3 is not None and not d3.empty:
        billed_map = dict(zip(d3['PLAYER_WYID'].apply(rens_id), d3['IMAGEDATAURL']))

    # 3. Find alle unikke navne fra scouting-db
    navne_liste = sorted(df_s['Navn'].unique().tolist())

    # 4. Vælg spillere
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0, key="c1")
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1), key="c2")

    def hent_alle_data(navn):
        # Find nyeste rapport for denne spiller i scouting_db
        s_match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if s_match.empty: return None
        
        n = s_match.iloc[0]
        pid = n['PID_CLEAN']
        
        # Billede: Prioritér Snowflake (d3), ellers byg selv
        img_fra_sql = billed_map.get(pid)
        
        res = {
            "navn": navn,
            "pid": pid,
            "img": img_fra_sql,
            "klub": n.get('Klub', 'Ukendt'),
            "pos": map_position(n.get('Pos', '')),
            "stats": {"Kampe": 0, "Mål": 0, "Assist": 0, "Min": 0},
            "scout": {k: n.get(k, '-') for k in ['Styrker', 'Vurdering', 'Status']},
            "r": {
                'Fart': n.get('Fart', 0.1), 'Teknik': n.get('Teknik', 0.1),
                'Beslut': n.get('Beslutsomhed', 0.1), 'Intel': n.get('Spilintelligens', 0.1),
                'Aggr': n.get('Aggresivitet', 0.1), 'Leder': n.get('Lederegenskaber', 0.1),
                'Att': n.get('Attitude', 0.1), 'Udh': n.get('Udholdenhed', 0.1)
            }
        }

        # Tilføj karriere-stats hvis pid findes i career_df
        if career_df is not None and not career_df.empty:
            cdf = career_df.copy()
            cdf.columns = [c.upper() for c in cdf.columns]
            # Sørg for at vi filtrerer på din aktuelle sæson
            c_m = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            if not c_m.empty:
                res["stats"] = {
                    "Kampe": int(c_m.iloc[0].get('APPEARANCES', 0)),
                    "Mål": int(c_m.iloc[0].get('GOAL', 0)),
                    "Assist": int(c_m.iloc[0].get('ASSIST', 0)),
                    "Min": int(c_m.iloc[0].get('MINUTESPLAYED', 0))
                }
        return res

    p1, p2 = hent_alle_data(s1_navn), hent_alle_data(s2_navn)

    # --- VISNING ---
    st.divider()
    c_img1, c_radar, c_img2 = st.columns([2, 4, 2])
    
    for i, p in enumerate([p1, p2]):
        if p:
            with (c_img1 if i == 0 else c_img2):
                if i == 1: st.markdown("<div style='text-align:right;'>", unsafe_allow_html=True)
                vis_spiller_billede(p["img"], p["pid"])
                st.subheader(p["navn"])
                st.caption(f"{p['pos']} | {p['klub']}")
                if i == 1: st.markdown("</div>", unsafe_allow_html=True)

    with c_radar:
        if p1 and p2:
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
                st.info(f"**Vurdering:**\n\n{p['scout'].get('Vurdering')}")
