import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    # 1. DATA LOAD
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].apply(rens_id)
        # Sørg for datoen er rigtig format til sortering
        df_s['Dato'] = pd.to_datetime(df_s['Dato']).dt.date
    except Exception as e:
        st.error(f"Fejl ved indlæsning af scouting_db.csv: {e}")
        return

    # Billed-map fra SQL
    billed_map = {}
    if sql_players is not None and not sql_players.empty:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # 2. OVERBLIKSTABEL (Alle rapporter)
    st.markdown("### 📋 Scouting Database")
    
    # Sorter så nyeste rapporter ligger øverst
    df_vis = df_s.sort_values(by=['Dato', 'Navn'], ascending=[False, True])
    
    st.dataframe(
        df_vis[['Dato', 'Navn', 'Klub', 'Position', 'Status', 'Rating_Avg', 'Scout']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Dato": st.column_config.DateColumn("Dato", format="DD/MM/YYYY"),
            "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
            "Status": st.column_config.TextColumn("Status")
        }
    )

    st.divider()

    # 3. VALG AF SPILLERPROFIL (Unikke navne)
    navne_liste = sorted(df_s['Navn'].unique().tolist())
    
    col_pick, _ = st.columns([1, 2])
    with col_pick:
        valgt_navn = st.selectbox("Vælg spiller for detaljeret profil", ["--- Vælg spiller ---"] + navne_liste)

    # 4. SPILLERPROFIL (Tabs)
    if valgt_navn != "--- Vælg spiller ---":
        # Hent den nyeste rapport for den valgte spiller til profilen
        s_match = df_s[df_s['Navn'] == valgt_navn].sort_values('Dato').iloc[-1]
        pid = rens_id(s_match.get('PLAYER_WYID'))
        img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"

        st.markdown(f"#### 👤 Spillerprofil: {valgt_navn}")
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.image(img_url, width=180)
            status = str(s_match.get('Status', 'Ukendt'))
            # Farve-logik baseret på status
            bg_color = "#df003b" if "Køb" in status or "Prioritet" in status else "#333"
            
            st.markdown(f"""
                <div style='background:{bg_color}; color:white; padding:10px; border-radius:5px; text-align:center; margin-top:10px;'>
                    <small>STATUS</small><br><b>{status.upper()}</b>
                </div>
            """, unsafe_allow_html=True)
            
            st.write(f"**Klub:** {s_match.get('Klub', 'Ukendt')}")
            st.write(f"**Position:** {s_match.get('Position', 'Ukendt')}")
            st.write(f"**Potentiale:** {s_match.get('Potentiale', '-')}")

        with c2:
            tab1, tab2, tab3 = st.tabs(["📝 Nyeste Rapport", "📊 Radar", "📈 Karriere"])
            
            with tab1:
                st.info(f"**Vurdering ({s_match['Dato']}):**\n\n{s_match.get('Vurdering', '-')}")
                col_s, col_u = st.columns(2)
                col_s.write(f"**Styrker:**\n{s_match.get('Styrker', '-')}")
                col_u.write(f"**Udvikling:**\n{s_match.get('Udvikling', '-')}")
                st.caption(f"Scoutet af: {s_match.get('Scout', 'Ukendt')}")
            
            with tab2:
                # Radar (Mapper direkte til dine kolonnenavne fra CSV)
                labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
                # Dette skal matche dine kolonneoverskrifter præcis:
                keys = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
                
                r_values = []
                for k in keys:
                    val = s_match.get(k, 0)
                    try:
                        v = float(str(val).replace(',', '.'))
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
                    height=350, margin=dict(l=50, r=50, t=30, b=30), showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                # Karriere-logik fra main.py argument
                if career_df is not None and not career_df.empty:
                    c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & 
                                    (career_df['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
                    if not c_m.empty:
                        st.dataframe(c_m[['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']], hide_index=True)
                    else:
                        st.write("Ingen karrere-data fundet i denne sæson.")
                else:
                    st.write("Karriere-database ikke tilgængelig.")
