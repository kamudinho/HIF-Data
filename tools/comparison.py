import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere is None or player_events is None or df_scout is None:
        st.error("Kunne ikke indlæse data.")
        return

    # --- 1. DEFINITIONER (Ordbogen) ---
    radar_defs = {
        'Tekniske færdigheder': 'Boldbehandling, førsteberøringer og pasningskvalitet.',
        'Beslutsomhed': 'Evnen til at træffe hurtige, korrekte valg under pres.',
        'Fart': 'Acceleration og topfart med og uden bold.',
        'Aggressivitet': 'Vished i dueller og fysisk tilstedeværelse.',
        'Attitude': 'Mentalitet, arbejdsrate og kropssprog.',
        'Udholdenhed': 'Evnen til at præstere på højt niveau i 90 minutter.',
        'Lederevner': 'Kommunikation og evne til at guide medspillere.',
        'Spilintelligens': 'Forståelse for positionering og læsning af spillet.'
    }

    # --- 2. FORBERED DATA ---
    df_hif = spillere.copy()
    df_hif['Full_Name'] = df_hif['FIRSTNAME'] + " " + df_hif['LASTNAME']
    df_scout.columns = [str(c).strip().upper() for c in df_scout.columns]
    
    hif_navne = df_hif[['Full_Name', 'PLAYER_WYID']].rename(columns={'Full_Name': 'Navn', 'PLAYER_WYID': 'ID'})
    scout_navne = df_scout[['NAVN', 'ID']].rename(columns={'NAVN': 'Navn', 'ID': 'ID'})
    
    samlet_df = pd.concat([hif_navne, scout_navne]).drop_duplicates(subset=['ID'])
    navne_liste = sorted(samlet_df['Navn'].unique())

    # --- 3. HJÆLPEFUNKTIONER ---
    def get_position_metrics(navn):
        try:
            pos = ""
            if navn in df_hif['Full_Name'].values:
                pos = df_hif[df_hif['Full_Name'] == navn]['POSITION'].iloc[0].upper()
            elif navn in df_scout['NAVN'].values:
                pos = df_scout[df_scout['NAVN'] == navn]['POSITION'].iloc[0].upper()
        except:
            pos = "ANGREB"

        if any(x in pos for x in ["GK", "MÅLMAND"]):
            return [("REDNINGER", "SAVES"), ("CLEAN SH.", "CLEANSHEETS"), ("UDSPARK %", "PASSACC"), 
                    ("EROBR.", "RECOVERIES"), ("DUEL %", "DEFDUELSWON"), ("PASNINGER", "PASSES")]
        elif any(x in pos for x in ["DEF", "FORSVAR", "BACK"]):
            return [("EROBR.", "RECOVERIES"), ("DUEL %", "DEFDUELSWON"), ("LUFT %", "AERIALDUELSWON"), 
                    ("FREM PAS", "FORWARDPASSES"), ("PAS %", "PASSACC"), ("BLOCKS", "SHOTSBLOCKED")]
        elif any(x in pos for x in ["MID", "MIDTBANE"]):
            return [("PAS %", "PASSACC"), ("FREM PAS", "FORWARDPASSES"), ("EROBR.", "RECOVERIES"), 
                    ("CHANCER", "ASSISTS"), ("DUEL %", "DEFDUELSWON"), ("xG", "XG")]
        else:
            return [("MÅL", "GOALS"), ("SKUD", "SHOTS"), ("xG", "XG"), 
                    ("BERØR. FELT", "TOUCHINBOX"), ("DRIBLE %", "DRIBBLESWON"), ("ASSISTS", "ASSISTS")]

    # --- 4. VALG AF SPILLERE ---
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2:
        s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

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
        stats_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(search_id, na=False)]
        stats = stats_match.iloc[0].to_dict() if not stats_match.empty else {}
        
        scout_match = df_scout[df_scout['ID'].astype(str).apply(clean_id) == search_id]
        tech_stats = {k: 0 for k in ['TEKNIK', 'BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'SPILINTELLIGENS']}
        scout_dict = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen vurdering fundet'}

        if not scout_match.empty:
            nyeste = scout_match.sort_values('DATO', ascending=False).iloc[0]
            for k in tech_stats.keys(): tech_stats[k] = nyeste.get(k, 0)
            scout_dict = {
                's': nyeste.get('STYRKER', 'Ingen data'),
                'u': f"**Potentiale:** {nyeste.get('POTENTIALE','')}\n\n**Udvikling:** {nyeste.get('UDVIKLING','')}",
                'v': nyeste.get('VURDERING', 'Ingen data')
            }
        return stats, scout_dict, tech_stats

    row1, scout1, tech1 = hent_spiller_data(s1_navn)
    row2, scout2, tech2 = hent_spiller_data(s2_navn)

    # --- 5. RADAR CHART ---
    categories = list(radar_defs.keys())
    cols_in_df = ['TEKNIK', 'BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'SPILINTELLIGENS']

    def get_radar_values(t_stats):
        vals = [t_stats.get(c, 0) for c in cols_in_df]
        return vals + [vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=get_radar_values(tech1), theta=categories + [categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
    fig.add_trace(go.Scatterpolar(r=get_radar_values(tech2), theta=categories + [categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
    
    fig.update_layout(
        polar=dict(
            gridshape='linear',
            radialaxis=dict(visible=True, range=[0, 6], tickfont=dict(size=9)),
            angularaxis=dict(tickfont=dict(size=10), rotation=90, direction="clockwise")
        ),
        showlegend=False, height=480, margin=dict(l=70, r=70, t=30, b=30), autosize=True
    )

    # --- 6. VISNING ---
    def vis_spiller_metrics(row, navn, side="venstre"):
        color = "#df003b" if side == "venstre" else "#0056a3"
        align = "left" if side == "venstre" else "right"
        st.markdown(f"<h4 style='color: {color}; text-align: {align}; margin-bottom: 5px;'>{navn}</h4>", unsafe_allow_html=True)
        
        # BASIS (2x2)
        b1, b2 = st.columns(2)
        with b1:
            st.metric("KAMPE", int(row.get('KAMPE', 0)), help="Antal kampe spillet")
            st.metric("GULE", int(row.get('YELLOWCARDS', 0)))
        with b2:
            st.metric("MIN.", int(row.get('MINUTESONFIELD', 0)), help="Minutter på banen")
            st.metric("RØDE", int(row.get('REDCARDS', 0)))
            
        st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
        
        # PERFORMANCE (3x2)
        pos_metrics = get_position_metrics(navn)
        p1, p2 = st.columns(2)
        for i, (label, key) in enumerate(pos_metrics):
            val = row.get(key, 0)
            target_col = p1 if i % 2 == 0 else p2
            with target_col:
                st.metric(label, int(val) if pd.notna(val) else 0)

    st.write("")
    c1, c2, c3 = st.columns([1.8, 3, 1.8])

    with c1:
        vis_spiller_metrics(row1, s1_navn, side="venstre")

    with c2:
        # Spørgsmålstegn placeret direkte i midten over grafen med tooltip
        st.markdown(f"<div style='text-align: right;' title='{chr(10).join([f'{k}: {v}' for k, v in radar_defs.items()])}'>❓</div>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with c3:
        vis_spiller_metrics(row2, s2_navn, side="højre")

    # --- 7. TABS (Scouting detaljer) ---
    st.write("") 
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown(f"<p style='color: #df003b; font-weight: bold;'>Scouting: {s1_navn}</p>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        with t1: st.info(scout1['s'])
        with t2: st.warning(scout1['u'])
        with t3: st.success(scout1['v'])
    with sc2:
        st.markdown(f"<p style='color: #0056a3; font-weight: bold; text-align: right;'>Scouting: {s2_navn}</p>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        with t1: st.info(scout2['s'])
        with t2: st.warning(scout2['u'])
        with t3: st.success(scout2['v'])
