import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere is None or player_events is None or df_scout is None:
        st.error("Kunne ikke indlæse de nødvendige data til sammenligning.")
        return

    # Forbered navneliste
    df_spillere = spillere.copy()
    df_spillere['Full_Name'] = df_spillere['FIRSTNAME'] + " " + df_spillere['LASTNAME']
    navne_liste = sorted(df_spillere['Full_Name'].unique())

    # --- TOP SEKTION: VALG AF SPILLERE ---
    col_sel1, col_sel2 = st.columns(2)

    with col_sel1:
        st.markdown("<h4 style='color: #df003b;'>Spiller 1</h4>", unsafe_allow_html=True)
        s1_navn = st.selectbox("Vælg P1", navne_liste, index=0, label_visibility="collapsed")

    with col_sel2:
        st.markdown("<h4 style='color: #0056a3; text-align: right;'>Spiller 2</h4>", unsafe_allow_html=True)
        s2_navn = st.selectbox("Vælg P2", navne_liste, index=1 if len(navne_liste) > 1 else 0,
                               label_visibility="collapsed")

    def hent_data(navn):
        # 1. Find PLAYER_WYID på spilleren fra spillerlisten
        p_id = df_spillere[df_spillere['Full_Name'] == navn]['PLAYER_WYID'].iloc[0]
        
        # 2. Hent Stats (Wyscout)
        stats = player_events[player_events['PLAYER_WYID'] == p_id].iloc[0]
        
        # 3. Rens kolonnenavne
        df_scout.columns = [str(c).strip() for c in df_scout.columns]
        
        # 4. Find matches i df_scout (hvor kolonnen hedder 'ID')
        scout_match = df_scout[df_scout['ID'].astype(str) == str(p_id)]
        
        if not scout_match.empty:
            scout_match = scout_match.sort_values('Dato', ascending=False)
            nyeste = scout_match.iloc[0]
            
            # Vi henter både Potentiale og Udvikling
            pot = nyeste.get('Potentiale', '')
            udv = nyeste.get('Udvikling', '')
            
            # Kombiner dem til én tekstblok hvis begge findes
            kombineret_udv = f"**Potentiale:** {pot}\n\n**Udvikling:** {udv}" if pot and udv else (pot or udv or "Ingen data")

            scout_dict = {
                's': nyeste.get('Styrker', 'Ingen data'),
                'u': kombineret_udv,
                'v': nyeste.get('Vurdering', 'Ingen data')
            }
        else:
            scout_dict = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen scouting fundet'}
            
        return stats, scout_dict

    # Hent data for begge spillere
    row1, scout1 = hent_data(s1_navn)
    row2, scout2 = hent_data(s2_navn)

    # Global max til radar-skalering
    stats_to_track = ['GOALS', 'FORWARDPASSES', 'SHOTS', 'RECOVERIES', 'PASSES', 'KAMPE', 'MINUTESONFIELD', 'TOUCHINBOX']
    max_stats = {s: (player_events[s].max() if player_events[s].max() > 0 else 1) for s in stats_to_track}

    st.divider()

    # --- LAYOUT: 3 KOLONNER ---
    c1, c2, c3 = st.columns([1.5, 2, 1.5])

    # SPILLER 1 (VENSTRE - RØD)
    with c1:
        st.markdown(f"<h3 style='color: #df003b;'>{s1_navn}</h3>", unsafe_allow_html=True)
        s1_m1, s1_m2 = st.columns(2)
        with s1_m1:
            st.metric("MÅL", int(row1['GOALS']))
            st.metric("SKUD", int(row1['SHOTS']))
        with s1_m2:
            st.metric("PASNINGER", int(row1['PASSES']))
            st.metric("EROBRINGER", int(row1['RECOVERIES']))
        
        st.write("") 
        st.success(f"**Styrker**\n\n{scout1['s']}")
        st.warning(f"**Udvikling**\n\n{scout1['u']}")
        st.info(f"**Vurdering**\n\n{scout1['v']}")

    # RADAR (MIDTEN)
    with c2:
        def get_radar_values(row):
            vals = [
                (row['GOALS'] / max_stats['GOALS']) * 100,
                (row['FORWARDPASSES'] / max_stats['FORWARDPASSES']) * 100,
                (row['SHOTS'] / max_stats['SHOTS']) * 100,
                (row['RECOVERIES'] / max_stats['RECOVERIES']) * 100,
                (row['PASSES'] / max_stats['PASSES']) * 100,
                (row['KAMPE'] / max_stats['KAMPE']) * 100,
                (row['MINUTESONFIELD'] / max_stats['MINUTESONFIELD']) * 100,
                (row['TOUCHINBOX'] / max_stats['TOUCHINBOX']) * 100
            ]
            return vals + [vals[0]]

        categories = ['Mål', 'Fremad. pass', 'Skud', 'Erobringer', 'Pasninger', 'Kampe', 'Minutter', 'Felt-berør.']
        categories_closed = categories + [categories[0]]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=get_radar_values(row1), theta=categories_closed, fill='toself', name=s1_navn, line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=get_radar_values(row2), theta=categories_closed, fill='toself', name=s2_navn, line_color='#0056a3'))
        
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False, 
            height=400, 
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    # SPILLER 2 (HØJRE - BLÅ)
    with c3:
        st.markdown(f"<h3 style='color: #0056a3; text-align: right;'>{s2_navn}</h3>", unsafe_allow_html=True)
        s2_m1, s2_m2 = st.columns(2)
        with s2_m1:
            st.metric("MÅL", int(row2['GOALS']))
            st.metric("SKUD", int(row2['SHOTS']))
        with s2_m2:
            st.metric("PASNINGER", int(row2['PASSES']))
            st.metric("EROBRINGER", int(row2['RECOVERIES']))

        st.write("") 
        st.success(f"**Styrker**\n\n{scout2['s']}")
        st.warning(f"**Udvikling**\n\n{scout2['u']}")
        st.info(f"**Vurdering**\n\n{scout2['v']}")
