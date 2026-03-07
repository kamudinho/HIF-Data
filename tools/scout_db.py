import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def map_position(pos_code):
    # Vi mapper de mest gængse talkoder direkte til HIF-termer
    # Hvis 'Pos' i din CSV er en tekst (f.eks. 'ANG'), returneres den bare.
    pos_dict = {
        "1": "MM", "2": "HB", "3": "VB", "4": "VCB", "5": "HCB", 
        "6": "DMC", "7": "HK", "8": "MC", "9": "ANG", "10": "OMC", "11": "VK"
    }
    clean_pos = rens_id(pos_code)
    return pos_dict.get(clean_pos, clean_pos) # Fallback til den oprindelige tekst hvis koden ikke findes

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    # 1. DATA LOAD
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].apply(rens_id)
    except:
        st.error("Kunne ikke indlæse scouting_db.csv")
        return

    # Billed-map fra SQL
    billed_map = {}
    if sql_players is not None and not sql_players.empty:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # 2. OVERBLIKSTABEL
    st.markdown("### 📋 Scouting Database")
    
    df_vis = df_s.copy()
    if 'Dato' in df_vis.columns:
        df_vis = df_vis.sort_values('Dato', ascending=False)
    
    # Vi mapper positionen i tabellen med det samme
    df_vis['Pos'] = df_vis['Pos'].apply(map_position)
    
    st.dataframe(
        df_vis[['Dato', 'Navn', 'Klub', 'Pos', 'Status', 'Vurdering']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["A-Emne", "B-Emne", "Hold øje", "Afskrevet"]),
            "Vurdering": st.column_config.TextColumn("Kort info", width="medium")
        }
    )

    st.divider()

    # 3. VALG AF SPILLERPROFIL
    navne_liste = sorted(df_s['Navn'].unique().tolist())
    
    col_pick, _ = st.columns([1, 2])
    with col_pick:
        valgt_navn = st.selectbox("Vælg spiller for at åbne detaljeret profil", ["--- Vælg spiller ---"] + navne_liste)

    # 4. SPILLERPROFIL (Tabs)
    if valgt_navn != "--- Vælg spiller ---":
        s_match = df_s[df_s['Navn'] == valgt_navn].sort_values('Dato').iloc[-1]
        pid = rens_id(s_match.get('PLAYER_WYID'))
        img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"

        st.markdown(f"#### 👤 Spillerprofil: {valgt_navn}")
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.image(img_url, width=180)
            status = s_match.get('Status', 'Ukendt')
            st.markdown(f"""
                <div style='background:#df003b; color:white; padding:10px; border-radius:5px; text-align:center; margin-top:10px;'>
                    <small>STATUS</small><br><b>{status}</b>
                </div>
            """, unsafe_allow_html=True)
            st.write(f"**Klub:** {s_match.get('Klub', 'Ukendt')}")
            st.write(f"**Position:** {map_position(s_match.get('Pos', ''))}")

        with c2:
            tab1, tab2, tab3 = st.tabs(["📝 Rapport", "📊 Radar", "📈 Karriere"])
            
            with tab1:
                st.info(f"**Vurdering:**\n\n{s_match.get('Vurdering', '-')}")
                st.write(f"**Styrker:** {s_match.get('Styrker', '-')}")
                st.write(f"**Svagheder:** {s_match.get('Svagheder', '-')}")
            
            with tab2:
                # Radar logik (8-kantet / Polygon)
                labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
                k = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
                
                r_values = []
                for val in k:
                    try:
                        raw = s_match.get(val, 0)
                        v = float(str(raw).replace(',', '.'))
                        r_values.append(v if v > 0 else 0.1)
                    except:
                        r_values.append(0.1)
                
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=r_values + [r_values[0]],
                    theta=labels + [labels[0]],
                    fill='toself',
                    line_color='#df003b'
                ))
                fig.update_layout(
                    polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])),
                    height=350, margin=dict(l=50, r=50, t=30, b=30),
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                if career_df is not None:
                    c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & 
                                    (career_df['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
                    if not c_m.empty:
                        st.dataframe(c_m[['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']], hide_index=True)
                    else:
                        st.write("Ingen karriere-data fundet for denne spiller.")
