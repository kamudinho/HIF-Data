import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- HJÆLPEFUNKTIONER ---
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

def vis_spiller_billede(img_url, pid, w=100):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    img_clean = str(img_url).strip() if pd.notna(img_url) else ""
    pid_clean = rens_id(pid)
    if img_clean and img_clean not in ["0", "0.0", "nan"]:
        url = img_clean
    elif pid_clean:
        url = f"https://cdn5.wyscout.com/photos/players/public/{pid_clean}.png"
    else:
        url = std
    st.image(url, width=w)

def render_stat_col(label, value, align="left"):
    # Hjælper med at lave det rene tal-look fra dit screenshot
    st.markdown(f"""
        <div style="text-align: {align}; margin-bottom: 10px;">
            <p style="margin:0; font-size: 0.8rem; color: gray; text-transform: uppercase;">{label}</p>
            <p style="margin:0; font-size: 1.8rem; font-weight: 700;">{value}</p>
        </div>
    """, unsafe_allow_html=True)

def vis_side(df_spillere, d1, d2, career_df, d3):
    # 1. DATA PREP
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except: return

    billed_map = {}
    if d3 is not None and not d3.empty:
        billed_map = dict(zip(d3['PLAYER_WYID'].apply(rens_id), d3['IMAGEDATAURL']))

    navne_liste = sorted(df_s['Navn'].unique().tolist())

    # 2. SELECTORS
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1))

    def hent_data(navn):
        s_match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if s_match.empty: return None
        n = s_match.iloc[0]
        pid = n['PID_CLEAN']
        
        # Hent ROLECODE3 og TEAMNAME fra df_spillere hvis muligt
        pos_str, klub_str = "Ukendt", "Ukendt"
        if df_spillere is not None and not df_spillere.empty:
            df_p = df_spillere.copy()
            df_p.columns = [c.upper() for c in df_p.columns]
            m = df_p[df_p['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos_str = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub_str = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')

        # Stats
        stats = {"Mål": 0, "Passes": 0, "Skud": 0, "Kampe": 0}
        if career_df is not None and not career_df.empty:
            cdf = career_df.copy()
            cdf.columns = [c.upper() for c in cdf.columns]
            c_m = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & (cdf['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {
                    "Mål": int(c_m.iloc[0].get('GOAL', 0)),
                    "Passes": int(c_m.iloc[0].get('PASSES', 0)),
                    "Skud": int(c_m.iloc[0].get('SHOTS', 0)),
                    "Kampe": int(c_m.iloc[0].get('APPEARANCES', 0))
                }

        return {
            "navn": navn, "pid": pid, "img": billed_map.get(pid),
            "pos": pos_str, "klub": klub_str, "stats": stats,
            "vurdering": n.get('Vurdering', 'Ingen noter fundet.'),
            "r": {k: n.get(k, 0.1) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']}
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)

    # 3. DASHBOARD RENDER
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Række 1: Navne og Billeder
    h1, h_space, h2 = st.columns([4, 1, 4])
    with h1:
        st.markdown(f"<h2 style='color:#df003b; margin-bottom:0;'>{p1['navn']}</h2>", unsafe_allow_html=True)
        c_img, c_txt = st.columns([1, 3])
        with c_img: vis_spiller_billede(p1["img"], p1["pid"], w=80)
        with c_txt: st.caption(f"{p1['pos']} | {p1['klub']}")
    
    with h2:
        st.markdown(f"<h2 style='color:#0056a3; margin-bottom:0; text-align:right;'>{p2['navn']}</h2>", unsafe_allow_html=True)
        c_txt, c_img = st.columns([3, 1])
        with c_img: vis_spiller_billede(p2["img"], p2["pid"], w=80)
        with c_txt: st.markdown(f"<div style='text-align:right; color:gray; font-size:0.9rem;'>{p2['pos']} | {p2['klub']}</div>", unsafe_allow_html=True)

    # Række 2: Stats - Radar - Stats
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Vi bruger 'gap' for at få luft, og sikrer at kolonnerne starter helt fra toppen
    s1, rad, s2 = st.columns([2, 5, 2], gap="small")
    
    with s1:
        # Flyt stats helt op ved at fjerne top-margin
        st.markdown('<div style="margin-top:-20px;">', unsafe_allow_html=True)
        render_stat_col("Mål", p1["stats"]["Mål"])
        render_stat_col("Passes", p1["stats"]["Passes"])
        render_stat_col("Skud", p1["stats"]["Skud"])
        render_stat_col("Kampe", p1["stats"]["Kampe"])
        st.markdown('</div>', unsafe_allow_html=True)

    with s2:
        st.markdown('<div style="margin-top:-20px;">', unsafe_allow_html=True)
        render_stat_col("Mål", p2["stats"]["Mål"], "right")
        render_stat_col("Passes", p2["stats"]["Passes"], "right")
        render_stat_col("Skud", p2["stats"]["Skud"], "right")
        render_stat_col("Kampe", p2["stats"]["Kampe"], "right")
        st.markdown('</div>', unsafe_allow_html=True)

    with rad:
        labels = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
        fig = go.Figure()
        
        # Tilføj spillere
        for p, color in [(p1, '#df003b'), (p2, '#0056a3')]:
            r_vals = [p['r'].get(k, 0.1) for k in ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']]
            fig.add_trace(go.Scatterpolar(
                r=r_vals + [r_vals[0]], 
                theta=labels + [labels[0]], 
                fill='toself', 
                name=p['navn'], 
                line_color=color,
                opacity=0.6
            ))

        # LAYOUT MED KANTER OG STYRING
        fig.update_layout(
            polar=dict(
                bgcolor="white",
                radialaxis=dict(
                    visible=True, 
                    range=[0, 6], 
                    gridcolor="#eeeeee", # Grå cirkel-kanter
                    linecolor="#444444",  # Midter-aksen
                    tickfont=dict(size=8)
                ),
                angularaxis=dict(
                    gridcolor="#eeeeee", # Kanter mellem "lagkagestykkerne"
                    linecolor="#444444", # Den yderste kant-ramme
                    direction="clockwise"
                )
            ),
            height=420, # Justeret højde
            margin=dict(l=40, r=40, t=0, b=0), # Fjern top-margin så den rykker op
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)", # Gennemsigtig baggrund
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
