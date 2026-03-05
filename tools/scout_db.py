import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

# --- HJÆLPEFUNKTIONER (Fra din profil-fil) ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.1
        v = float(str(val).replace(',', '.'))
        return v if v > 0 else 0.1
    except: return 0.1

def map_position(pos_code):
    pos_dict = {"1": "MM", "2": "HB", "3": "VB", "4": "VCB", "5": "HCB", "6": "DMC", "7": "HK", "8": "MC", "9": "ANG", "10": "OMC", "11": "VK"}
    clean_pos = rens_id(pos_code)
    return pos_dict.get(clean_pos, "Ukendt")

def vis_side(df_spillere, d1, d2, career_df, sql_players):
    # --- 1. DATA PREP ---
    # Vi bruger sql_players (d3) til billed-opslag, præcis som i din profil-fil
    billed_map = {}
    if sql_players is not None and not sql_players.empty:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # Scouting data (fra CSV)
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].apply(rens_id)
    except:
        df_s = pd.DataFrame()

    # Spillerliste til selectbox
    navne_liste = sorted(list(set(df_s['Navn'].tolist() if not df_s.empty else [])))
    
    if not navne_liste:
        st.warning("Ingen spillere fundet i scouting_db.csv")
        return

    # --- 2. SELECTORS ---
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1))

    def hent_alle_data(navn):
        if df_s.empty: return None
        
        # Find nyeste scouting rapport for navnet
        s_match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if s_match.empty: return None
        
        n = s_match.iloc[0]
        pid = rens_id(n.get('PLAYER_WYID'))
        
        # Hent billede fra map (SQL) eller fallback til CDN
        img_url = billed_map.get(pid)
        if not img_url:
            img_url = f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"

        res = {
            "navn": navn,
            "pid": pid,
            "img": img_url,
            "klub": n.get('Klub', 'Ukendt'),
            "pos": map_position(n.get('Pos', '')),
            "scout": {
                "Styrker": n.get('Styrker', '-'),
                "Vurdering": n.get('Vurdering', '-'),
                "Status": n.get('Status', '-')
            },
            "r": {
                'Fart': rens_metrik_vaerdi(n.get('Fart')),
                'Teknik': rens_metrik_vaerdi(n.get('Teknik')),
                'Beslut': rens_metrik_vaerdi(n.get('Beslutsomhed')),
                'Intel': rens_metrik_vaerdi(n.get('Spilintelligens')),
                'Aggr': rens_metrik_vaerdi(n.get('Aggresivitet')),
                'Leder': rens_metrik_vaerdi(n.get('Lederegenskaber')),
                'Att': rens_metrik_vaerdi(n.get('Attitude')),
                'Udh': rens_metrik_vaerdi(n.get('Udholdenhed'))
            }
        }

        # Karriere Stats
        stats = {"Kampe": 0, "Mål": 0, "Min": 0}
        if career_df is not None and not career_df.empty:
            cdf = career_df.copy()
            cdf.columns = [str(c).upper() for c in cdf.columns]
            cdf['PLAYER_WYID'] = cdf['PLAYER_WYID'].apply(rens_id)
            
            c_m = cdf[(cdf['PLAYER_WYID'] == pid) & (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            if not c_m.empty:
                stats = {
                    "Kampe": int(c_m.iloc[0].get('APPEARANCES', 0)),
                    "Mål": int(c_m.iloc[0].get('GOAL', 0)),
                    "Min": int(c_m.iloc[0].get('MINUTESPLAYED', 0))
                }
        res["stats"] = stats
        return res

    p1, p2 = hent_alle_data(s1_navn), hent_alle_data(s2_navn)

    # --- 3. VISNING ---
    st.divider()
    h1, h_radar, h2 = st.columns([2, 4, 2])

    with h1:
        if p1:
            st.image(p1["img"], width=130)
            st.subheader(p1["navn"])
            st.caption(f"{p1['pos']} | {p1['klub']}")

    with h2:
        if p2:
            # Højrestillet billede og tekst
            st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
            st.image(p2["img"], width=130)
            st.subheader(p2["navn"])
            st.caption(f"{p2['pos']} | {p2['klub']}")
            st.markdown("</div>", unsafe_allow_html=True)

    with h_radar:
        if p1 and p2:
            categories = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
            k = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=[p1['r'][x] for x in k]+[p1['r'][k[0]]], theta=categories+[categories[0]], fill='toself', name=p1['navn'], line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=[p2['r'][x] for x in k]+[p2['r'][k[0]]], theta=categories+[categories[0]], fill='toself', name=p2['navn'], line_color='#0056a3'))
            
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), height=350, margin=dict(l=40,r=40,t=20,b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # Stats tabeller
    st.divider()
    col_a, col_b = st.columns(2)
    for i, p in enumerate([p1, p2]):
        with (col_a if i == 0 else col_b):
            if p:
                st.write(f"### 📊 Stats ({SEASON_FILTER})")
                st.table(pd.DataFrame([p["stats"]], index=["Antal"]).T)
                st.info(f"**Vurdering:**\n\n{p['scout']['Vurdering']}")
