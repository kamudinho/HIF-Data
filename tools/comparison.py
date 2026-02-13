import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere is None or player_events is None or df_scout is None:
        st.error("Kunne ikke indlæse data.")
        return

    # --- 1. FORBERED DEN KOMBINEREDE NAVNELISTE ---
    df_hif = spillere.copy()
    df_hif['Full_Name'] = df_hif['FIRSTNAME'] + " " + df_hif['LASTNAME']
    df_scout.columns = [str(c).strip().upper() for c in df_scout.columns]
    
    hif_navne = df_hif[['Full_Name', 'PLAYER_WYID']].rename(columns={'Full_Name': 'Navn', 'PLAYER_WYID': 'ID'})
    scout_navne = df_scout[['NAVN', 'ID']].rename(columns={'NAVN': 'Navn', 'ID': 'ID'})
    
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
        try:
            p_id = samlet_df[samlet_df['Navn'] == navn]['ID'].iloc[0]
        except:
            return {}, {}, {k: 0 for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']}

        def clean_id(val):
            if pd.isna(val) or val == "": return "0"
            try: return str(int(float(val)))
            except: return str(val).strip()

        search_id = clean_id(p_id)

        # A) Wyscout Stats
        stats_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(search_id, na=False)]
        stats = stats_match.iloc[0].to_dict() if not stats_match.empty else {}
        
        # B) Scouting Data
        scout_match = df_scout[df_scout['ID'].astype(str).apply(clean_id) == search_id]
        
        tech_stats = {k: 0 for k in ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']}
        scout_dict = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen vurdering fundet'}

        if not scout_match.empty:
            nyeste = scout_match.sort_values('DATO', ascending=False).iloc[0]
            for k in tech_stats.keys():
                tech_stats[k] = nyeste.get(k, 0)

            pot = nyeste.get('POTENTIALE', '')
            udv = nyeste.get('UDVIKLING', '')
            komb_udv = f"**Potentiale:** {pot}\n\n**Udvikling:** {udv}" if pot or udv else "Ingen data"

            scout_dict = {
                's': nyeste.get('STYRKER', 'Ingen data'),
                'u': komb_udv,
                'v': nyeste.get('VURDERING', 'Ingen data')
            }
            
        return stats, scout_dict, tech_stats

    row1, scout1, tech1 = hent_spiller_data(s1_navn)
    row2, scout2, tech2 = hent_spiller_data(s2_navn)

    # --- 4. RADAR CHART LOGIK (SKALA 1-6) ---
    categories = ['Beslutsomhed', 'Fart', 'Aggressivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
    cols_in_df = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']

    def get_radar_values(t_stats):
        vals = [t_stats.get(c, 0) for c in cols_in_df]
        return vals + [vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=get_radar_values(tech1), theta=categories + [categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
    fig.add_trace(go.Scatterpolar(r=get_radar_values(tech2), theta=categories + [categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
    
    fig.update_layout(
        polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6], tickmode='linear', tick0=0, dtick=1)),
        showlegend=False, height=420, margin=dict(l=50, r=50, t=30, b=30)
    )

    # --- 5. VISNING AF METRICS OG RADAR ---
    st.write("")
    c1, c2, c3 = st.columns([1.2, 2, 1.2])

    # Ensartede Wyscout Metrics for begge spillere
    metrics_list = [
        ("MÅL", "GOALS"),
        ("SKUD", "SHOTS"),
        ("PASNINGER", "PASSES"),
        ("EROBRINGER", "RECOVERIES")
    ]

    with c1:
        st.markdown(f"<h4 style='color: #df003b; margin-bottom: 0;'>{s1_navn}</h4>", unsafe_allow_html=True)
        for label, key in metrics_list:
            st.metric(f"{label} (WY)", int(row1.get(key, 0)))

    with c2:
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        st.markdown(f"<h4 style='color: #0056a3; text-align: right; margin-bottom: 0;'>{s2_navn}</h4>", unsafe_allow_html=True)
        for label, key in metrics_list:
            st.metric(f"{label} (WY)", int(row2.get(key, 0)))

    # --- 6. BUND SEKTION: TABS ---
    st.write("") 
    sc1, sc2 = st.columns(2)

    with sc1:
        st.markdown(f"<p style='color: #df003b; font-weight: bold; margin-bottom: 5px;'>Scouting: {s1_navn}</p>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        with t1: st.info(scout1['s'])
        with t2: st.warning(scout1['u'])
        with t3: st.success(scout1['v'])

    with sc2:
        st.markdown(f"<p style='color: #0056a3; font-weight: bold; text-align: right; margin-bottom: 5px;'>Scouting: {s2_navn}</p>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        with t1: st.info(scout2['s'])
        with t2: st.warning(scout2['u'])
        with t3: st.success(scout2['v'])
