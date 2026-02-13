import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere is None or player_events is None or df_scout is None:
        st.error("Kunne ikke indlæse data.")
        return

    # --- 1. DEFINITIONER ---
    radar_defs = {
        'Beslutsomhed': 'BESLUTSOMHED',
        'Fart': 'FART',
        'Aggressivitet': 'AGGRESIVITET',
        'Attitude': 'ATTITUDE',
        'Udholdenhed': 'UDHOLDENHED',
        'Lederevner': 'LEDEREGENSKABER',
        'Teknik': 'TEKNIK',
        'Spil-int.': 'SPILINTELLIGENS'
    }

    def get_position_metrics(navn, df_hif, df_scout):
        try:
            pos = "UNKNOWN"
            # Søg i HIF data
            if navn in df_hif['Full_Name'].values:
                pos = df_hif[df_hif['Full_Name'] == navn]['POSITION'].iloc[0]
            # Søg i Scout data
            elif navn in df_scout['NAVN'].values:
                pos = df_scout[df_scout['NAVN'] == navn]['POSITION'].iloc[0]
            pos = str(pos).upper()
        except: pos = "UNKNOWN"

        if any(x in pos for x in ["GK", "MÅLMAND"]):
            return [("REDNINGER", "SAVES"), ("CLEAN SH.", "CLEANSHEETS"), ("UDSPARK %", "PASSACC"), ("EROBR.", "RECOVERIES"), ("DUEL %", "DEFDUELSWON"), ("PASNINGER", "PASSES")]
        elif any(x in pos for x in ["DEF", "FORSVAR", "BACK"]):
            return [("EROBR.", "RECOVERIES"), ("DUEL %", "DEFDUELSWON"), ("LUFT %", "AERIALDUELSWON"), ("FREM PAS", "FORWARDPASSES"), ("PAS %", "PASSACC"), ("BLOCKS", "SHOTSBLOCKED")]
        elif any(x in pos for x in ["MID", "MIDTBANE"]):
            return [("PAS %", "PASSACC"), ("FREM PAS", "FORWARDPASSES"), ("EROBR.", "RECOVERIES"), ("CHANCER", "ASSISTS"), ("DUEL %", "DEFDUELSWON"), ("xG", "XG")]
        else:
            return [("MÅL", "GOALS"), ("SKUD", "SHOTS"), ("xG", "XG"), ("BERØR. FELT", "TOUCHINBOX"), ("DRIBLE %", "DRIBBLESWON"), ("ASSISTS", "ASSISTS")]

    # --- 2. FORBERED DATA ---
    df_hif = spillere.copy()
    df_hif['Full_Name'] = df_hif['FIRSTNAME'] + " " + df_hif['LASTNAME']
    df_scout.columns = [str(c).strip().upper() for c in df_scout.columns]
    
    hif_navne = df_hif[['Full_Name', 'PLAYER_WYID']].rename(columns={'Full_Name': 'Navn', 'PLAYER_WYID': 'ID'})
    scout_navne = df_scout[['NAVN', 'ID']].rename(columns={'NAVN': 'Navn', 'ID': 'ID'})
    
    samlet_df = pd.concat([hif_navne, scout_navne]).drop_duplicates(subset=['Navn'])
    navne_liste = sorted(samlet_df['Navn'].unique())

    # --- 3. VALG AF SPILLERE ---
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    # --- 4. ROBUST DATA HENTNING ---
    def hent_spiller_data(navn):
        try:
            # Find ID
            p_id = samlet_df[samlet_df['Navn'] == navn]['ID'].iloc[0]
            # Rens ID til sammenligning (fjerner .0)
            def clean(val): return str(int(float(val))) if pd.notna(val) and str(val)!="0" else "0"
            search_id = clean(p_id)
            
            # Find Klub og Position (Søger både på ID og Navn)
            klub, pos = "Ukendt klub", "Ukendt"
            
            # Check HIF først
            hif_match = df_hif[df_hif['Full_Name'] == navn]
            if not hif_match.empty:
                klub = "Hillerød Fodbold"
                pos = hif_match['POSITION'].iloc[0]
            else:
                # Check Scout ark
                scout_info = df_scout[df_scout['NAVN'] == navn]
                if not scout_info.empty:
                    klub = scout_info['KLUB'].iloc[0] if 'KLUB' in scout_info.columns else "Scouted"
                    pos = scout_info['POSITION'].iloc[0] if 'POSITION' in scout_info.columns else "Ukendt"

            # Wyscout Stats (Events)
            stats = {}
            if search_id != "0":
                stats_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(search_id, na=False)]
                if not stats_match.empty:
                    stats = stats_match.iloc[0].to_dict()

            # Radar Stats
            tech_stats = {k: 0 for k in radar_defs.values()}
            scout_dict = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen vurdering', 'klub': klub, 'pos': pos, 'id': p_id}

            # Find scouting række (prioritér ID, ellers Navn)
            scout_row = df_scout[df_scout['ID'].apply(clean) == search_id]
            if scout_row.empty:
                scout_row = df_scout[df_scout['NAVN'] == navn]

            if not scout_row.empty:
                nyeste = scout_row.sort_values('DATO', ascending=False).iloc[0]
                for k in tech_stats.keys(): tech_stats[k] = nyeste.get(k, 0)
                scout_dict.update({
                    's': nyeste.get('STYRKER', 'Ingen data'),
                    'u': f"**Potentiale:** {nyeste.get('POTENTIALE','')}\n\n**Udvikling:** {nyeste.get('UDVIKLING','')}",
                    'v': nyeste.get('VURDERING', 'Ingen data')
                })
            
            return stats, scout_dict, tech_stats
        except Exception as e:
            return {}, {'s': 'Fejl', 'u': 'Fejl', 'v': 'Fejl', 'klub': 'Ukendt', 'pos': 'Ukendt', 'id': 0}, {k: 0 for k in radar_defs.values()}

    row1, scout1, tech1 = hent_spiller_data(s1_navn)
    row2, scout2, tech2 = hent_spiller_data(s2_navn)

    # --- 5. RADAR CHART ---
    categories = list(radar_defs.keys())
    cols_in_df = list(radar_defs.values())
    def get_radar_values(t_stats):
        vals = [t_stats.get(c, 0) for c in cols_in_df]
        return vals + [vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=get_radar_values(tech1), theta=categories + [categories[0]], fill='toself', name=s1_navn, line_color='#df003b', hovertemplate="%{theta}: %{r}<extra></extra>"))
    fig.add_trace(go.Scatterpolar(r=get_radar_values(tech2), theta=categories + [categories[0]], fill='toself', name=s2_navn, line_color='#0056a3', hovertemplate="%{theta}: %{r}<extra></extra>"))
    
    fig.update_layout(
        polar=dict(
            gridshape='linear',
            radialaxis=dict(visible=True, range=[0, 6], tickvals=[1,2,3,4,5,6], showticklabels=False, gridcolor="rgba(128,128,128,0.4)"),
            angularaxis=dict(tickfont=dict(size=10), rotation=90, direction="clockwise", gridcolor="rgba(128,128,128,0.4)")
        ),
        showlegend=False, height=480, margin=dict(l=80, r=80, t=30, b=30)
    )

    # --- 6. VISNINGSFUNKTION ---
    def vis_metrics(row, scout_info, navn, color, side):
        align = "left" if side == "venstre" else "right"
        fallback_img = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
        
        try:
            p_id = scout_info['id']
            clean_id = str(int(float(p_id))) if pd.notna(p_id) and str(p_id) != "0" else None
            img_url = f"https://cdn5.wyscout.com/photos/players/public/g-{clean_id}_100x130.png" if clean_id else fallback_img
        except: img_url = fallback_img

        if side == "venstre":
            col_img, col_txt = st.columns([1, 2.5])
            with col_img: st.image(img_url, width=85)
            with col_txt:
                st.markdown(f"<h4 style='color:{color}; margin-bottom: 0px;'>{navn}</h4>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:gray; font-size:13px; margin-top: 0px;'>{scout_info['pos']} | {scout_info['klub']}</p>", unsafe_allow_html=True)
        else:
            col_txt, col_img = st.columns([2.5, 1])
            with col_txt:
                st.markdown(f"<h4 style='color:{color}; text-align:right; margin-bottom: 0px;'>{navn}</h4>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:gray; font-size:13px; text-align:right; margin-top: 0px;'>{scout_info['pos']} | {scout_info['klub']}</p>", unsafe_allow_html=True)
            with col_img: st.image(img_url, width=85)
        
        st.write("")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("KAMPE", int(row.get('KAMPE', 0)))
            st.metric("GULE", int(row.get('YELLOWCARDS', 0)))
        with col_b:
            st.metric("MIN.", int(row.get('MINUTESONFIELD', 0)))
            st.metric("RØDE", int(row.get('REDCARDS', 0)))
        
        st.write("---")
        p1, p2 = st.columns(2)
        for i, (label, key) in enumerate(get_position_metrics(navn, df_hif, df_scout)):
            target = p1 if i % 2 == 0 else p2
            target.metric(label, int(row.get(key, 0)) if pd.notna(row.get(key, 0)) else 0)

    # --- PLACERING ---
    c1, c2, c3 = st.columns([2.3, 3, 2.3])
    with c1: vis_metrics(row1, scout1, s1_navn, "#df003b", "venstre")
    with c2: st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    with c3: vis_metrics(row2, scout2, s2_navn, "#0056a3", "højre")

    # --- 7. TABS ---
    st.write("---")
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
