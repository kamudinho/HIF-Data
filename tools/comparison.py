import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(spillere, player_events, df_scout):
    if spillere is None or player_events is None or df_scout is None:
        st.error("Kunne ikke indlæse de nødvendige data til sammenligning.")
        return

    df_spillere = spillere.copy()
    df_spillere['Full_Name'] = df_spillere['FIRSTNAME'] + " " + df_spillere['LASTNAME']
    navne_liste = sorted(df_spillere['Full_Name'].unique())

    col_sel1, col_sel2 = st.columns(2)

    with col_sel1:
        st.markdown("<h4 style='color: #df003b;'>🔴 Spiller 1</h4>", unsafe_allow_html=True)
        s1_navn = st.selectbox("Vælg P1", navne_liste, index=0, label_visibility="collapsed")

    with col_sel2:
        st.markdown("<h4 style='color: #0056a3; text-align: right;'>🔵 Spiller 2</h4>", unsafe_allow_html=True)
        s2_navn = st.selectbox("Vælg P2", navne_liste, index=1 if len(navne_liste) > 1 else 0,
                               label_visibility="collapsed")

    def hent_data(navn):
        p_id = df_spillere[df_spillere['Full_Name'] == navn]['PLAYER_WYID'].iloc[0]
        stats = player_events[player_events['PLAYER_WYID'] == p_id].iloc[0]
        df_scout.columns = [str(c).strip().upper() for c in df_scout.columns]
        scout_match = df_scout[df_scout['PLAYER_WYID'] == p_id]
        beskrivelse = "Ingen scouting-notater fundet."
        if not scout_match.empty and 'BESKRIVELSE' in df_scout.columns:
            beskrivelse = scout_match['BESKRIVELSE'].iloc[0]
        return stats, beskrivelse

    row1, desc1 = hent_data(s1_navn)
    row2, desc2 = hent_data(s2_navn)

    stats_to_track = ['GOALS', 'FORWARDPASSES', 'SHOTS', 'RECOVERIES', 'PASSES', 'KAMPE', 'MINUTESONFIELD', 'TOUCHINBOX']
    max_stats = {s: (player_events[s].max() if player_events[s].max() > 0 else 1) for s in stats_to_track}

    st.divider()

    c1, c2, c3 = st.columns([1.3, 2, 1.3])

    # SPILLER 1 (VENSTRE - RØD)
    with c1:
        st.markdown(f"<h3 style='color: #df003b;'>{s1_navn}</h3>", unsafe_allow_html=True)
        s1_col_a, s1_col_b = st.columns(2)
        with s1_col_a:
            st.metric("MÅL", int(row1['GOALS']))
            st.metric("SKUD", int(row1['SHOTS']))
            st.metric("BERØRINGER I FELTET", int(row1['TOUCHINBOX']))
        with s1_col_b:
            st.metric("PASSES", int(row1['PASSES']))
            st.metric("FREMADRETTEDE PASSES", int(row1['FORWARDPASSES']))
            st.metric("EROBRINGER", int(row1['RECOVERIES']))

        st.markdown(f"""
            <div style="background-color: rgba(223, 0, 59, 0.1); border-left: 5px solid #df003b; padding: 15px; border-radius: 5px;">
                <strong style="color: #df003b;">Scout vurdering:</strong><br><br>
                {desc1}
            </div>
        """, unsafe_allow_html=True)

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

        categories = ['Mål', 'Fremadrettede passes.', 'Skud', 'Erobringer', 'Pasninger', 'Kampe', 'Minutter', 'Berøringer i felt.']
        categories_closed = categories + [categories[0]]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=get_radar_values(row1), theta=categories_closed, fill='toself', name=s1_navn, line_color='#df003b'))
        fig.add_trace(go.Scatterpolar(r=get_radar_values(row2), theta=categories_closed, fill='toself', name=s2_navn, line_color='#0056a3'))
        fig.update_layout(polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=450, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig, use_container_width=True)

    # SPILLER 2 (HØJRE - BLÅ)
    with c3:
        st.markdown(f"<h3 style='color: #0056a3; text-align: right;'>{s2_navn}</h3>", unsafe_allow_html=True)
        s2_col_a, s2_col_b = st.columns(2)
        with s2_col_a:
            st.metric("MÅL", int(row2['GOALS']))
            st.metric("SKUD", int(row2['SHOTS']))
            st.metric("BERØRINGER I FELTET", int(row2['TOUCHINBOX']))
        with s2_col_b:
            st.metric("PASSES", int(row2['PASSES']))
            st.metric("FREMADRETTEDE PASSES", int(row2['FORWARDPASSES']))
            st.metric("EROBRINGER", int(row2['RECOVERIES']))

        st.markdown(f"""
            <div style="background-color: rgba(0, 86, 163, 0.1); border-right: 5px solid #0056a3; padding: 15px; border-radius: 5px; text-align: right;">
                <strong style="color: #0056a3;">Scout vurdering:</strong><br><br>
                {desc2}
            </div>
        """, unsafe_allow_html=True)