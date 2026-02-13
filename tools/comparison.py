import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere is None or player_events is None or df_scout is None:
        st.error("Kunne ikke indlæse data.")
        return

    # --- 1. DEFINITIONER (Bruges til Hover i selve grafen) ---
    radar_defs = {
        'Tekniske færdigheder': 'Boldbehandling, førsteberøringer og pasningskvalitet.',
        'Beslutsomhed': 'Evnen til at træffe hurtige, korrekte valg under pres.',
        'Fart': 'Acceleration og topfart med og uden bold.',
        'Aggressivitet': 'Vished i dueller og fysisk tilstedeværelse.',
        'Attitude': 'Mentalitet, arbejdsrate og kropssprog.',
        'Udholdenhed': 'Evnen til at præstere på højt niveau i 90 minutter.',
        'Lederevner': 'Kommunikation og evne til at dirigere medspillere.',
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

    # --- 4. VALG AF SPILLERE ---
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        s1_navn = st.selectbox("Vælg Spiller 1", navne_liste, index=0)
    with col_sel2:
        s2_navn = st.selectbox("Vælg Spiller 2", navne_liste, index=1 if len(navne_liste) > 1 else 0)

    # Funktion til at hente data
    def hent_spiller_data(navn):
        empty_tech = {k: 0 for k in ['TEKNIK', 'BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'SPILINTELLIGENS']}
        try:
            p_id = samlet_df[samlet_df['Navn'] == navn]['ID'].iloc[0]
            search_id = str(int(float(p_id))) if pd.notna(p_id) else "0"
            
            stats_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(search_id, na=False)]
            stats = stats_match.iloc[0].to_dict() if not stats_match.empty else {}
            
            scout_match = df_scout[df_scout['ID'].astype(str).str.replace('.0','',regex=False) == search_id]
            tech_stats = empty_tech.copy()
            scout_dict = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen vurdering fundet'}

            if not scout_match.empty:
                nyeste = scout_match.sort_values('DATO', ascending=False).iloc[0]
                tech_stats = {
                    'TEKNIK': nyeste.get('TEKNIK', 0),
                    'BESLUTSOMHED': nyeste.get('BESLUTSOMHED', 0),
                    'FART': nyeste.get('FART', 0),
                    'AGGRESIVITET': nyeste.get('AGGRESIVITET', 0),
                    'ATTITUDE': nyeste.get('ATTITUDE', 0),
                    'UDHOLDENHED': nyeste.get('UDHOLDENHED', 0),
                    'LEDEREGENSKABER': nyeste.get('LEDEREGENSKABER', 0),
                    'SPILINTELLIGENS': nyeste.get('SPILINTELLIGENS', 0)
                }
                scout_dict = {'s': nyeste.get('STYRKER', 'Ingen data'), 'u': nyeste.get('POTENTIALE', 'Ingen data'), 'v': nyeste.get('VURDERING', 'Ingen data')}
            return stats, scout_dict, tech_stats
        except:
            return {}, {'s': 'Fejl', 'u': 'Fejl', 'v': 'Fejl'}, empty_tech

    row1, scout1, tech1 = hent_spiller_data(s1_navn)
    row2, scout2, tech2 = hent_spiller_data(s2_navn)

    # --- 5. RADAR CHART MED INDBYGGET HOVER (Annotationer) ---
    categories = list(radar_defs.keys())
    hover_texts = [radar_defs[cat] for cat in categories]
    cols_in_df = ['TEKNIK', 'BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'SPILINTELLIGENS']

    def get_radar_values(t_stats):
        vals = [t_stats.get(c, 0) for c in cols_in_df]
        return vals + [vals[0]]

    fig = go.Figure()
    
    # Spiller 1 - Hover info tilføjet her
    fig.add_trace(go.Scatterpolar(
        r=get_radar_values(tech1),
        theta=categories + [categories[0]],
        fill='toself',
        name=s1_navn,
        line_color='#df003b',
        hoverinfo="text+r",
        text=hover_texts + [hover_texts[0]]
    ))
    
    # Spiller 2 - Hover info tilføjet her
    fig.add_trace(go.Scatterpolar(
        r=get_radar_values(tech2),
        theta=categories + [categories[0]],
        fill='toself',
        name=s2_navn,
        line_color='#0056a3',
        hoverinfo="text+r",
        text=hover_texts + [hover_texts[0]]
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 6]),
            angularaxis=dict(direction="clockwise", rotation=90)
        ),
        showlegend=False, height=450, margin=dict(l=50, r=50, t=20, b=20)
    )

    # --- 6. LAYOUT ---
    def vis_metrics(row, navn, color):
        st.markdown(f"<h4 style='color:{color};'>{navn}</h4>", unsafe_allow_html=True)
        c_a, c_b = st.columns(2)
        c_a.metric("KAMPE", int(row.get('KAMPE', 0)))
        c_b.metric("MIN.", int(row.get('MINUTESONFIELD', 0)))
        st.write("---")
        # Pladsspecifikke metrics her (forkortet for stabilitet)
        st.metric("GULE KORT", int(row.get('YELLOWCARDS', 0)))

    col1, col2, col3 = st.columns([2, 3, 2])
    
    with col1:
        vis_metrics(row1, s1_navn, "#df003b")

    with col2:
        # INGEN IKONER HER - Alt er indbygget i fig (Plotly)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col3:
        vis_metrics(row2, s2_navn, "#0056a3")

    # --- 7. TABS ---
    st.write("---")
    t_left, t_right = st.columns(2)
    with t_left:
        tab1, tab2, tab3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        tab1.write(scout1['s'])
        tab2.write(scout1['u'])
        tab3.write(scout1['v'])
    with t_right:
        tab1, tab2, tab3 = st.tabs(["Styrker", "Udvikling", "Vurdering"])
        tab1.write(scout2['s'])
        tab2.write(scout2['u'])
        tab3.write(scout2['v'])
