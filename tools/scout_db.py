import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def map_position(pos_code):
    pos_dict = {"1": "MM", "2": "HB", "3": "VB", "4": "VCB", "5": "HCB", "6": "DMC", "7": "HK", "8": "MC", "9": "ANG", "10": "OMC", "11": "VK"}
    return pos_dict.get(rens_id(pos_code), "Ukendt")

# --- HOVEDFUNKTION (Rettet til at modtage de 4 argumenter fra din main.py) ---
def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    
    # 1. Hent den rå database
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

    # 2. Søge- og valgsektion
    st.markdown("### 📋 Scouting Database")
    
    navne_liste = sorted(df_s['Navn'].unique().tolist())
    valgt_navn = st.selectbox("Søg og vælg spiller for at se detaljer", ["Vælg spiller..."] + navne_liste)

    if valgt_navn == "Vælg spiller...":
        st.info("Vælg en spiller ovenfor for at åbne deres profil.")
        # Her kan du evt. vise en oversigtstabel over alle rapporter som fallback
        return

    # 3. Data-hentning for valgt spiller
    s_match = df_s[df_s['Navn'] == valgt_navn].sort_values('Dato').iloc[-1]
    pid = rens_id(s_match.get('PLAYER_WYID'))
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"

    # 4. Detalje-sektion (Åbner når spiller er valgt)
    st.divider()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(img_url, width=200)
        st.header(valgt_navn)
        st.subheader(f"{map_position(s_match.get('Pos', ''))} | {s_match.get('Klub', 'Ukendt')}")
        
        # Status Badge
        status = s_match.get('Status', 'Ukendt')
        color = "#df003b" if "A" in status else "#b8860b"
        st.markdown(f"<div style='background:{color}; color:white; padding:5px 10px; border-radius:5px; text-align:center; font-weight:bold;'>{status}</div>", unsafe_allow_html=True)

    with col2:
        tab1, tab2, tab3 = st.tabs(["Scout Rapport", "Radar", "Karriere"])
        
        with tab1:
            st.markdown(f"**Styrker:**\n{s_match.get('Styrker', '-')}")
            st.markdown(f"**Svagheder:**\n{s_match.get('Svagheder', '-')}")
            st.info(f"**Vurdering:**\n\n{s_match.get('Vurdering', '-')}")
            
        with tab2:
            # Radar Logik
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
            k = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
            r_values = [float(str(s_match.get(val, 0)).replace(',', '.')) for val in k]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=r_values + [r_values[0]],
                theta=labels + [labels[0]],
                fill='toself',
                line_color='#df003b'
            ))
            fig.update_layout(
                polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])),
                height=350, margin=dict(l=40, r=40, t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            if career_df is not None:
                c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & 
                                (career_df['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
                if not c_m.empty:
                    st.table(c_m[['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']])
                else:
                    st.write("Ingen karriere-data fundet for denne sæson.")
