import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- HJÆLPEFUNKTIONER ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

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

def vis_side(df_spillere, d1, d2, career_df, d3):
    # 1. DATA PREP
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except:
        st.error("Kunne ikke læse scouting_db.csv")
        return

    billed_map = {}
    if d3 is not None and not d3.empty:
        billed_map = dict(zip(d3['PLAYER_WYID'].apply(rens_id), d3['IMAGEDATAURL']))

    navne_liste = sorted(df_s['Navn'].unique().tolist())

    # 2. SELECTORS (Flottere placeret)
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1))

    def hent_data(navn):
        s_match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if s_match.empty: return None
        n = s_match.iloc[0]
        pid = n['PID_CLEAN']
        
        # Karrierestats
        stats = {"Kampe": 0, "Mål": 0, "Assist": 0, "Min": 0}
        if career_df is not None and not career_df.empty:
            cdf = career_df.copy()
            cdf.columns = [c.upper() for c in cdf.columns]
            # Bruger SEASON_FILTER fra din main eller definer her
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
            "klub": n.get('Klub', 'Ukendt'), "pos": n.get('Pos', 'Ukendt'),
            "vurdering": n.get('Vurdering', '-'), "styrker": n.get('Styrker', '-'),
            "stats": stats,
            "r": {
                'Fart': n.get('Fart', 0), 'Teknik': n.get('Teknik', 0),
                'Beslut': n.get('Beslutsomhed', 0), 'Intel': n.get('Spilintelligens', 0),
                'Aggr': n.get('Aggresivitet', 0), 'Leder': n.get('Lederegenskaber', 0),
                'Att': n.get('Attitude', 0), 'Udh': n.get('Udholdenhed', 0)
            }
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)

    if not p1 or not p2:
        st.warning("Vælg to spillere for at sammenligne")
        return

    # 3. HOVEDLAYOUT (Visuals)
    st.markdown("---")
    
    # Øverste sektion med billeder og Radar
    c1, c_radar, c2 = st.columns([1.5, 3.5, 1.5])

    with c1:
        st.markdown("<br>", unsafe_allow_html=True)
        vis_spiller_billede(p1["img"], p1["pid"])
        st.subheader(p1["navn"])
        st.markdown(f"**{p1['pos']}** \n*{p1['klub']}*")

    with c2:
        st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        vis_spiller_billede(p2["img"], p2["pid"])
        st.subheader(p2["navn"])
        st.markdown(f"**{p2['pos']}** \n*{p2['klub']}*")
        st.markdown("</div>", unsafe_allow_html=True)

    with c_radar:
        labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
        keys = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=[p1['r'][k] for k in keys]+[p1['r'][keys[0]]], theta=labels+[labels[0]], fill='toself', name=p1['navn'], line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=[p2['r'][k] for k in keys]+[p2['r'][keys[0]]], theta=labels+[labels[0]], fill='toself', name=p2['navn'], line_color='#0056a3'))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 6], gridcolor="lightgrey")),
            height=450, margin=dict(l=60, r=60, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)

    # 4. STATS SAMMENLIGNING (Side om side tabel)
    st.markdown("### 📊 Statistisk Sammenligning")
    
    # Vi bygger en DataFrame til sammenligning
    comparison_data = {
        "Kategori": ["Kampe", "Minutter", "Mål", "Assists"],
        p1["navn"]: [p1["stats"]["Kampe"], p1["stats"]["Min"], p1["stats"]["Mål"], p1["stats"]["Assist"]],
        p2["navn"]: [p2["stats"]["Kampe"], p2["stats"]["Min"], p2["stats"]["Mål"], p2["stats"]["Assist"]]
    }
    st.table(pd.DataFrame(comparison_data).set_index("Kategori"))

    # 5. SCOUT NOTER
    st.markdown("---")
    n1, n2 = st.columns(2)
    with n1:
        st.markdown(f"#### 📝 {p1['navn']}")
        st.success(f"**Styrker:** {p1['styrker']}")
        st.info(f"**Vurdering:** {p1['vurdering']}")
    with n2:
        st.markdown(f"#### 📝 {p2['navn']}")
        st.success(f"**Styrker:** {p2['styrker']}")
        st.info(f"**Vurdering:** {p2['vurdering']}")
