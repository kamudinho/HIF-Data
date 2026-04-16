import streamlit as st
import pandas as pd

def vis_side():
    # 1. Hent data fra session_state (hvor dine andre modstander-analyser gemmer dem)
    # Hvis dine andre sider gemmer modstander-data under et andet navn, så ret det her
    df_input = st.session_state.get('df_all_h', None)

    if df_input is None:
        st.warning("⚠️ Ingen data fundet. Gå venligst til 'Intern analyse' eller 'Modstanderanalyse' først og vælg et hold.")
        return

    st.markdown("### PHYSICAL & TECHNICAL PROFILES")
    st.write("De 5 mest kampafgørende profiler baseret på statistisk impact")

    # --- BEREGNINGSLOGIK ---
    # Vi grupperer på PLAYER_NAME og trækker relevante stats
    player_stats = df_input.groupby('PLAYER_NAME').agg(
        Touches_Box=('EVENT_X', lambda x: ((df_input.loc[x.index, 'EVENT_X'] > 83) & 
                                           (df_input.loc[x.index, 'EVENT_Y'].between(21, 79))).sum()),
        Gennembrud=('EVENT_TYPEID', lambda x: ((df_input.loc[x.index, 'EVENT_TYPEID'] == 1) & 
                                               (df_input.loc[x.index, 'EVENT_X'] > 70)).sum()),
        Dueller=('EVENT_TYPEID', lambda x: x.isin([7, 44]).sum()),
        Chancer=('qual_list', lambda x: x.apply(lambda q: '210' in q or '209' in q).sum())
    ).reset_index()

    player_stats['Score'] = (player_stats['Touches_Box'] * 3) + (player_stats['Gennembrud'] * 1.5) + (player_stats['Chancer'] * 2)
    top_5 = player_stats.sort_values('Score', ascending=False).head(5)

    # --- VISNING I KOLONNER ---
    cols = st.columns(5)
    farver = ["#df003b", "#084594", "#238b45", "#ec7014"]

    for i, (idx, row) in enumerate(top_5.iterrows()):
        with cols[i]:
            efternavn = row['PLAYER_NAME'].split()[-1].upper()
            st.markdown(f"**{efternavn}**")
            st.caption(row['PLAYER_NAME'])
            st.markdown("<hr style='margin:10px 0; border:1px solid #eee'>", unsafe_allow_html=True)
            
            def draw_bar(label, val, max_val, color):
                percent = min(int((val / max_val) * 100), 100) if max_val > 0 else 0
                st.markdown(f"""
                    <div style="font-size: 10px; color: #666; margin-top: 8px; text-transform: uppercase;">{label}</div>
                    <div style="background-color: #f1f1f1; border-radius: 3px; height: 6px; width: 100%;">
                        <div style="background-color: {color}; height: 6px; width: {percent}%; border-radius: 3px;"></div>
                    </div>
                    <div style="font-size: 10px; font-weight: bold; text-align: right; margin-top: 2px;">{int(val)}</div>
                """, unsafe_allow_html=True)

            draw_bar("Box Touches", row['Touches_Box'], player_stats['Touches_Box'].max(), farver[0])
            draw_bar("Gennembrud", row['Gennembrud'], player_stats['Gennembrud'].max(), farver[1])
            draw_bar("Dueller", row['Dueller'], player_stats['Dueller'].max(), farver[2])
            draw_bar("Chancer", row['Chancer'], player_stats['Chancer'].max(), farver[3])
