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

def vis_spiller_billede(img_url, pid, w=80):
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
    st.markdown(f"""
        <div style="text-align: {align}; margin-bottom: 8px;">
            <p style="margin:0; font-size: 0.7rem; color: #888; text-transform: uppercase; font-weight: bold;">{label}</p>
            <p style="margin:0; font-size: 1.5rem; font-weight: 800; line-height: 1;">{value}</p>
        </div>
    """, unsafe_allow_html=True)

def vis_side(df_spillere, d1, d2, career_df, d3):
    # 1. DATA LOADING
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
    s1_navn = c_sel1.selectbox("Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Spiller 2", navne_liste, index=min(1, len(navne_liste)-1))

    def hent_data(navn):
        s_match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if s_match.empty: return None
        n = s_match.iloc[0]
        pid = n['PID_CLEAN']
        
        pos_str, klub_str = "Ukendt", "Ukendt"
        if df_spillere is not None and not df_spillere.empty:
            df_p = df_spillere.copy()
            df_p.columns = [c.upper() for c in df_p.columns]
            m = df_p[df_p['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos_str = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub_str = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')

        stats = {"Kampe": 0, "Mål": 0, "Assist": 0, "Min": 0}
        if career_df is not None and not career_df.empty:
            cdf = career_df.copy()
            cdf.columns = [c.upper() for c in cdf.columns]
            c_m = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & (cdf['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {
                    "Kampe": int(c_m.iloc[0].get('APPEARANCES', 0)),
                    "Mål": int(c_m.iloc[0].get('GOAL', 0)),
                    "Assist": int(c_m.iloc[0].get('ASSIST', 0)),
                    "Min": int(c_m.iloc[0].get('MINUTESPLAYED', 0))
                }

        return {
            "navn": navn, "pid": pid, "img": billed_map.get(pid),
            "pos": pos_str, "klub": klub_str, "stats": stats,
            "vurdering": n.get('Vurdering', '-'),
            "r": {
                'Fart': n.get('Fart', 0.1), 'Teknik': n.get('Teknik', 0.1),
                'Beslut': n.get('Beslutsomhed', 0.1), 'Intel': n.get('Spilintelligens', 0.1),
                'Aggr': n.get('Aggresivitet', 0.1), 'Leder': n.get('Lederegenskaber', 0.1),
                'Att': n.get('Attitude', 0.1), 'Udh': n.get('Udholdenhed', 0.1)
            }
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)

    # 3. DASHBOARD RENDER
    st.markdown("<hr style='margin:5px 0;'>", unsafe_allow_html=True)
    
    # Header
    h1, h2 = st.columns(2)
    with h1:
        st.markdown(f"<h2 style='color:#df003b; margin:0;'>{p1['navn']}</h2>", unsafe_allow_html=True)
        c_i, c_t = st.columns([1, 4])
        with c_i: vis_spiller_billede(p1["img"], p1["pid"])
        with c_t: st.markdown(f"<p style='color:gray; font-size:0.85rem;'>{p1['pos']}<br>{p1['klub']}</p>", unsafe_allow_html=True)
    with h2:
        st.markdown(f"<h2 style='color:#0056a3; margin:0; text-align:right;'>{p2['navn']}</h2>", unsafe_allow_html=True)
        c_t, c_i = st.columns([4, 1])
        with c_i: vis_spiller_billede(p2["img"], p2["pid"])
        with c_t: st.markdown(f"<div style='text-align:right; color:gray; font-size:0.85rem;'>{p2['pos']}<br>{p2['klub']}</div>", unsafe_allow_html=True)

    # Centreret Layout (Stats - Radar - Stats)
    st.markdown("<div style='margin-top: -50px;'>", unsafe_allow_html=True)
    s1, rad, s2 = st.columns([2, 5, 2])
    
    with s1:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        for k, v in p1["stats"].items(): render_stat_col(k, v)

    with s2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        for k, v in p2["stats"].items(): render_stat_col(k, v, "right")

    with rad:
        labels = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
        fig = go.Figure()
        
        for p, color in [(p1, '#df003b'), (p2, '#0056a3')]:
            r_vals = [p['r'][k] for k in ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']]
            fig.add_trace(go.Scatterpolar(r=r_vals+[r_vals[0]], theta=labels+[labels[0]], fill='toself', name=p['navn'], line_color=color))

        fig.update_layout(
            polar=dict(
                gridshape='linear', # HER ER 8-KANTEN!
                radialaxis=dict(visible=True, range=[0, 6], gridcolor="#ddd", linecolor="#000"),
                angularaxis=dict(gridcolor="#ddd", linecolor="#000", linewidth=2)
            ),
            height=480, margin=dict(l=50, r=50, t=10, b=10),
            showlegend=False, paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

    # Scout vurdering
    v1, v2 = st.columns(2)
    v1.markdown(f"<div style='background:#fff0f3; padding:12px; border-left:5px solid #df003b; border-radius:4px;'><b>Scout vurdering:</b><br>{p1['vurdering']}</div>", unsafe_allow_html=True)
    v2.markdown(f"<div style='background:#f0f7ff; padding:12px; border-right:5px solid #0056a3; border-radius:4px; text-align:right;'><b>Scout vurdering:</b><br>{p2['vurdering']}</div>", unsafe_allow_html=True)
