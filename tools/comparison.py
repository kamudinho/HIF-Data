import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- HJÆLPEFUNKTIONER ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def vis_spiller_billede(img_url, pid, w=130):
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
    # --- 1. DATA PREP ---
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

    # --- 2. SELECTORS (Pænt placeret i toppen) ---
    c_sel1, c_space, c_sel2 = st.columns([4, 1, 4])
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1))

    def hent_data(navn):
        s_match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if s_match.empty: return None
        n = s_match.iloc[0]
        pid = n['PID_CLEAN']
        
        # Scouting værdier (Radar)
        r_data = {
            'Fart': n.get('Fart', 0), 'Teknik': n.get('Teknik', 0),
            'Beslut': n.get('Beslutsomhed', 0), 'Intel': n.get('Spilintelligens', 0),
            'Aggr': n.get('Aggresivitet', 0), 'Leder': n.get('Lederegenskaber', 0),
            'Att': n.get('Attitude', 0), 'Udh': n.get('Udholdenhed', 0)
        }
        
        return {
            "navn": navn, "pid": pid, "img": billed_map.get(pid),
            "klub": n.get('Klub', 'Hvidovre IF'), "pos": n.get('Pos', 'Ukendt'),
            "vurdering": n.get('Vurdering', '-'), "styrker": n.get('Styrker', '-'),
            "r": r_data
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)

    # --- 3. VISUEL SAMMENLIGNING ---
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Hovedsektion: Billede - Radar - Billede
    c1, c_radar, c2 = st.columns([1.5, 3, 1.5])

    if p1:
        with c1:
            vis_spiller_billede(p1["img"], p1["pid"])
            st.subheader(p1["navn"])
            st.caption(f"📍 {p1['pos']} \n\n 🏠 {p1['klub']}")
    
    if p2:
        with c2:
            # Højrestillet profil for spiller 2
            st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
            vis_spiller_billede(p2["img"], p2["pid"])
            st.subheader(p2["navn"])
            st.caption(f"{p2['pos']} 📍 \n\n {p2['klub']} 🏠")
            st.markdown("</div>", unsafe_allow_html=True)

    with c_radar:
        if p1 and p2:
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
            keys = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
            
            fig = go.Figure()
            # Spiller 1 (Rød)
            fig.add_trace(go.Scatterpolar(
                r=[p1['r'][k] for k in keys] + [p1['r'][keys[0]]],
                theta=labels + [labels[0]],
                fill='toself', name=p1['navn'], line_color='#df003b', opacity=0.7
            ))
            # Spiller 2 (Blå)
            fig.add_trace(go.Scatterpolar(
                r=[p2['r'][k] for k in keys] + [p2['r'][keys[0]]],
                theta=labels + [labels[0]],
                fill='toself', name=p2['navn'], line_color='#0056a3', opacity=0.7
            ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 6], gridcolor="#eee")),
                height=400, margin=dict(l=50, r=50, t=30, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- 4. SCOUT NOTER (Split view) ---
    st.divider()
    n1, n2 = st.columns(2)
    
    for i, p in enumerate([p1, p2]):
        with (n1 if i == 0 else n2):
            if p:
                st.markdown(f"#### 📝 Scout Noter: {p['navn']}")
                st.info(f"**Styrker:**\n{p['styrker']}")
                with st.expander("Se fuld vurdering"):
                    st.write(p['vurdering'])
