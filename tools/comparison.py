import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere is None or player_events is None or df_scout is None:
        st.error("Kunne ikke indlæse data.")
        return

    # --- 1. FORBERED DEN KOMBINEREDE NAVNELISTE ---
    # HIF Spillere fra Excel
    df_hif = spillere.copy()
    df_hif['Full_Name'] = df_hif['FIRSTNAME'] + " " + df_hif['LASTNAME']
    
    # Scouting Spillere fra CSV (Vi tvinger kolonner til upper for en sikkerheds skyld)
    df_scout.columns = [str(c).strip().upper() for c in df_scout.columns]
    
    # Lav en liste over alle unikke navne fra begge kilder
    hif_navne = df_hif[['Full_Name', 'PLAYER_WYID']].rename(columns={'Full_Name': 'Navn', 'PLAYER_WYID': 'ID'})
    scout_navne = df_scout[['NAVN', 'ID']].rename(columns={'NAVN': 'Navn', 'ID': 'ID'})
    
    # Saml dem og fjern dubletter baseret på ID
    samlet_df = pd.concat([hif_navne, scout_navne]).drop_duplicates(subset=['ID'])
    navne_liste = sorted(samlet_df['Navn'].unique())

    # --- 2. VALG AF SPILLERE ---
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2:
        s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    # --- 3. HJÆLPEFUNKTION TIL AT HENTE DATA ---
    def hent_spiller_data(navn):
        # Find ID
        try:
            p_id = samlet_df[samlet_df['Navn'] == navn]['ID'].iloc[0]
        except:
            return {k: 0 for k in ['GOALS', 'SHOTS', 'PASSES', 'RECOVERIES']}, {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Spiller ikke fundet'}

        # Sikker konvertering af ID til streng (håndterer både 1234, 1234.0 og "1234")
        def clean_id(val):
            if pd.isna(val) or val == "": return "0"
            try:
                # Forsøg at fjerne .0 hvis det er en float gemt som streng
                return str(int(float(val)))
            except:
                return str(val).strip()

        search_id = clean_id(p_id)

        # A) Hent Stats (Wyscout)
        stats_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(search_id, na=False)]
        if not stats_match.empty:
            stats = stats_match.iloc[0]
        else:
            stats = {k: 0 for k in ['GOALS', 'SHOTS', 'PASSES', 'RECOVERIES', 'FORWARDPASSES', 'KAMPE', 'MINUTESONFIELD', 'TOUCHINBOX']}
        
        # B) Hent Scouting Tekst
        # Vi tjekker mod 'ID' kolonnen i df_scout
        scout_match = df_scout[df_scout['ID'].astype(str).apply(clean_id) == search_id]
        
        if not scout_match.empty:
            nyeste = scout_match.sort_values('DATO', ascending=False).iloc[0]
            
            pot = nyeste.get('POTENTIALE', '')
            udv = nyeste.get('UDVIKLING', '')
            pot_str = str(pot) if pd.notna(pot) and str(pot).lower() != "nan" else ""
            udv_str = str(udv) if pd.notna(udv) and str(udv).lower() != "nan" else ""
            
            komb_udv = ""
            if pot_str: komb_udv += f"**Potentiale:** {pot_str}\n\n"
            if udv_str: komb_udv += f"**Udvikling:** {udv_str}"

            scout_dict = {
                's': nyeste.get('STYRKER', 'Ingen data'),
                'u': komb_udv if komb_udv else "Ingen data",
                'v': nyeste.get('VURDERING', 'Ingen data')
            }
        else:
            scout_dict = {'s': 'Ingen scouting data', 'u': 'Ingen scouting data', 'v': 'Ingen vurdering fundet'}
            
        return stats, scout_dict
    row1, scout1 = hent_spiller_data(s1_navn)
    row2, scout2 = hent_spiller_data(s2_navn)

    # --- 4. RADAR CHART LOGIK ---
    stats_to_track = ['GOALS', 'FORWARDPASSES', 'SHOTS', 'RECOVERIES', 'PASSES', 'TOUCHINBOX']
    # Beregn max værdier for skalering (undgå division med 0)
    max_stats = {s: (player_events[s].max() if s in player_events and player_events[s].max() > 0 else 1) for s in stats_to_track}

    def get_radar_values(row):
        vals = []
        for s in stats_to_track:
            val = row.get(s, 0)
            max_val = max_stats[s]
            vals.append((val / max_val) * 100 if max_val > 0 else 0)
        return vals + [vals[0]]

    categories = ['Mål', 'Fremad. pass', 'Skud', 'Erobringer', 'Pasninger', 'Felt-berør.']
    categories_closed = categories + [categories[0]]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=get_radar_values(row1), theta=categories_closed, fill='toself', name=s1_navn, line_color='#df003b'))
    fig.add_trace(go.Scatterpolar(r=get_radar_values(row2), theta=categories_closed, fill='toself', name=s2_navn, line_color='#0056a3'))
    
    fig.update_layout(
        polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, height=450, margin=dict(l=50, r=50, t=50, b=50)
    )

    # --- 5. VISNING AF METRICS OG RADAR ---
    # Vi fjerner divideren her og bruger en container til at styre afstanden
    main_container = st.container()
    
    with main_container:
        c1, c2, c3 = st.columns([1.2, 2, 1.2])

        with c1:
            st.markdown(f"<h3 style='color: #df003b; margin-bottom: 0;'>{s1_navn}</h3>", unsafe_allow_html=True)
            st.metric("MÅL", int(row1.get('GOALS', 0)))
            st.metric("SKUD", int(row1.get('SHOTS', 0)))
            st.metric("PASNINGER", int(row1.get('PASSES', 0)))
            st.metric("EROBRINGER", int(row1.get('RECOVERIES', 0)))

        with c2:
            # Vi fjerner margin i selve plotly figuren for at spare plads opad
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with c3:
            st.markdown(f"<h3 style='color: #0056a3; text-align: right; margin-bottom: 0;'>{s2_navn}</h3>", unsafe_allow_html=True)
            st.metric("MÅL", int(row2.get('GOALS', 0)))
            st.metric("SKUD", int(row2.get('SHOTS', 0)))
            st.metric("PASNINGER", int(row2.get('PASSES', 0)))
            st.metric("EROBRINGER", int(row2.get('RECOVERIES', 0)))

   # --- 6. BUND SEKTION: TABS (Optimeret afstand) ---
    st.write("") # Tilføjer en enkelt linje luft efter radaren
    sc1, sc2 = st.columns(2)

    with sc1:
        # Vi bruger 5px margin i stedet for -10px for at undgå overlap
        st.markdown(f"<p style='color: #df003b; font-weight: bold; margin-bottom: 5px;'>Scouting: {s1_navn}</p>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        with t1: st.info(scout1['s'])
        with t2: st.warning(scout1['u'])
        with t3: st.success(scout1['v'])

    with sc2:
        # Højrejusteret tekst med korrekt afstand
        st.markdown(f"<p style='color: #0056a3; font-weight: bold; text-align: right; margin-bottom: 5px;'>Scouting: {s2_navn}</p>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        with t1: st.info(scout2['s']) # Rettet til scout2 her
        with t2: st.warning(scout2['u'])
        with t3: st.success(scout2['v'])
