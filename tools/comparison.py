import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere is None or player_events is None or df_scout is None:
        st.error("Kunne ikke indlæse data.")
        return

    # --- 1. DEFINITIONER (Rækkefølgen her styrer radaren) ---
    radar_defs = {
        'Tekniske færdigheder': 'Boldbehandling, førsteberøringer og pasningskvalitet.',
        'Beslutsomhed': 'Evnen til at træffe hurtige, korrekte valg under pres.',
        'Fart': 'Acceleration og topfart med og uden bold.',
        'Aggressivitet': 'Vished i dueller og fysisk tilstedeværelse.',
        'Attitude': 'Mentalitet, arbejdsrate og kropssprog.',
        'Udholdenhed': 'Evnen til at præstere på højt niveau i 90 minutter.',
        'Lederevner': 'Kommunikation og evne til at dirigere medspillere.',
        'Spilintelligens': 'Forståelse for positionering og evne til at læse spillet.'
    }

    # --- 2. FORBERED DATA (Beholdes præcis som før) ---
    df_hif = spillere.copy()
    df_hif['Full_Name'] = df_hif['FIRSTNAME'] + " " + df_hif['LASTNAME']
    df_scout.columns = [str(c).strip().upper() for c in df_scout.columns]
    
    hif_navne = df_hif[['Full_Name', 'PLAYER_WYID']].rename(columns={'Full_Name': 'Navn', 'PLAYER_WYID': 'ID'})
    scout_navne = df_scout[['NAVN', 'ID']].rename(columns={'NAVN': 'Navn', 'ID': 'ID'})
    
    samlet_df = pd.concat([hif_navne, scout_navne]).drop_duplicates(subset=['ID'])
    navne_liste = sorted(samlet_df['Navn'].unique())

    # --- 3. HJÆLPEFUNKTIONER (Original logik) ---
    def get_position_metrics(navn):
        try:
            pos = ""
            if navn in df_hif['Full_Name'].values:
                pos = df_hif[df_hif['Full_Name'] == navn]['POSITION'].iloc[0].upper()
            elif navn in df_scout['NAVN'].values:
                pos = df_scout[df_scout['NAVN'] == navn]['POSITION'].iloc[0].upper()
        except: pos = "ANGREB"

        if any(x in pos for x in ["GK", "MÅLMAND"]):
            return [("REDNINGER", "SAVES"), ("CLEAN SH.", "CLEANSHEETS"), ("UDSPARK %", "PASSACC"), ("EROBR.", "RECOVERIES"), ("DUEL %", "DEFDUELSWON"), ("PASNINGER", "PASSES")]
        elif any(x in pos for x in ["DEF", "FORSVAR", "BACK"]):
            return [("EROBR.", "RECOVERIES"), ("DUEL %", "DEFDUELSWON"), ("LUFT %", "AERIALDUELSWON"), ("FREM PAS", "FORWARDPASSES"), ("PAS %", "PASSACC"), ("BLOCKS", "SHOTSBLOCKED")]
        elif any(x in pos for x in ["MID", "MIDTBANE"]):
            return [("PAS %", "PASSACC"), ("FREM PAS", "FORWARDPASSES"), ("EROBR.", "RECOVERIES"), ("CHANCER", "ASSISTS"), ("DUEL %", "DEFDUELSWON"), ("xG", "XG")]
        else:
            return [("MÅL", "GOALS"), ("SKUD", "SHOTS"), ("xG", "XG"), ("BERØR. FELT", "TOUCHINBOX"), ("DRIBLE %", "DRIBBLESWON"), ("ASSISTS", "ASSISTS")]

    # --- 4. VALG AF SPILLERE ---
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2: s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    def hent_spiller_data(navn):
        try:
            p_id = samlet_df[samlet_df['Navn'] == navn]['ID'].iloc[0]
            search_id = str(int(float(p_id))) if pd.notna(p_id) else "0"
            stats = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(search_id, na=False)].iloc[0].to_dict()
            scout_match = df_scout[df_scout['ID'].astype(str).str.replace('.0','',regex=False) == search_id]
            tech_stats = {k: 0 for k in ['TEKNIK', 'BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'SPILINTELLIGENS']}
            scout_dict = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen vurdering'}
            if not scout_match.empty:
                nyeste = scout_match.sort_values('DATO', ascending=False).iloc[0]
                tech_stats = { 'TEKNIK': nyeste.get('TEKNIK', 0), 'BESLUTSOMHED': nyeste.get('BESLUTSOMHED', 0), 'FART': nyeste.get('FART', 0), 'AGGRESIVITET': nyeste.get('AGGRESIVITET', 0), 'ATTITUDE': nyeste.get('ATTITUDE', 0), 'UDHOLDENHED': nyeste.get('UDHOLDENHED', 0), 'LEDEREGENSKABER': nyeste.get('LEDEREGENSKABER', 0), 'SPILINTELLIGENS': nyeste.get('SPILINTELLIGENS', 0) }
                scout_dict = {'s': nyeste.get('STYRKER', 'Ingen data'), 'u': f"**Potentiale:** {nyeste.get('POTENTIALE','')}\n\n**Udvikling:** {nyeste.get('UDVIKLING','')}", 'v': nyeste.get('VURDERING', 'Ingen data')}
            return stats, scout_dict, tech_stats
        except: return {}, {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen data'}, {k: 0 for k in ['TEKNIK', 'BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'SPILINTELLIGENS']}

    row1, scout1, tech1 = hent_spiller_data(s1_navn)
    row2, scout2, tech2 = hent_spiller_data(s2_navn)

    # --- 5. RADAR CHART (Kantet, Rent Look med korrekte navne) ---
    categories = list(radar_defs.keys()) # Her henter den "Tekniske færdigheder" fra din ordbog
    
    # Her fortæller vi koden, hvilke kolonner i Excel den skal parre med kategorierne i radaren
    cols_in_df = ['TEKNIK', 'BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'SPILINTELLIGENS']

    fig = go.Figure()
    
    # Spiller 1
    fig.add_trace(go.Scatterpolar(
        r=[tech1.get(c, 0) for c in cols_in_df] + [tech1.get(cols_in_df[0], 0)], 
        theta=categories + [categories[0]], 
        fill='toself', 
        name=s1_navn, 
        line_color='#df003b', 
        hoverinfo="theta+r" 
    ))
    
    # Spiller 2
    fig.add_trace(go.Scatterpolar(
        r=[tech2.get(c, 0) for c in cols_in_df] + [tech2.get(cols_in_df[0], 0)], 
        theta=categories + [categories[0]], 
        fill='toself', 
        name=s2_navn, 
        line_color='#0056a3', 
        hoverinfo="theta+r" 
    ))
    
    fig.update_layout(
        polar=dict(
            gridshape='linear', 
            radialaxis=dict(
                visible=True, 
                range=[0, 6], 
                tickvals=[0, 1, 2, 3, 4, 5, 6],
                gridcolor="lightgray"
            ),
            angularaxis=dict(
                direction="clockwise", 
                rotation=90,
                gridcolor="lightgray",
                tickfont=dict(size=10) # Gør teksten på kategorierne nem at læse
            )
        ),
        showlegend=False, 
        height=480, 
        margin=dict(l=80, r=80, t=30, b=30)
    )
    
    # --- 6. VISNING (DIT ORIGINALE LAYOUT) ---
    def vis_metrics(row, navn, color, side):
        align = "left" if side == "venstre" else "right"
        st.markdown(f"<h4 style='color:{color}; text-align:{align};'>{navn}</h4>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        col_a.metric("KAMPE", int(row.get('KAMPE', 0)))
        col_b.metric("MIN.", int(row.get('MINUTESONFIELD', 0)))
        st.write("---")
        p1, p2 = st.columns(2)
        for i, (label, key) in enumerate(get_position_metrics(navn)):
            target = p1 if i % 2 == 0 else p2
            target.metric(label, int(row.get(key, 0)) if pd.notna(row.get(key, 0)) else 0)

    c1, c2, c3 = st.columns([1.8, 3, 1.8])
    with c1: vis_metrics(row1, s1_navn, "#df003b", "venstre")
    with c2: st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    with c3: vis_metrics(row2, s2_navn, "#0056a3", "højre")

    # --- 7. TABS ---
    st.write("---")
    sc1, sc2 = st.columns(2)
    with sc1:
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t1.info(scout1['s']); t2.warning(scout1['u']); t3.success(scout1['v'])
    with sc2:
        t1, t2, t3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        t1.info(scout2['s']); t2.warning(scout2['u']); t3.success(scout2['v'])
