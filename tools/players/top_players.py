import streamlit as st
import pandas as pd

# Brug df_all_h som input, da det er det navn, du bruger til modstander-data
def vis_side(df_input):
    # Tjek om dataframe er tomt eller ikke eksisterer
    if df_input is None or df_input.empty:
        st.warning("Ingen spillerdata tilgængelig for den valgte modstander.")
        return

    st.markdown("### PHYSICAL & TECHNICAL PROFILES")
    st.write(f"De 5 mest kampafgørende profiler baseret på seneste aktioner")

    # 1. BEREGN IMPACT (Vi bruger de kolonner, vi ved findes i dine Opta-data)
    # Vi grupperer på PLAYER_NAME
    stats = df_input.groupby('PLAYER_NAME').agg(
        Touches_Box=('EVENT_X', lambda x: ((df_input.loc[x.index, 'EVENT_X'] > 83) & 
                                           (df_input.loc[x.index, 'EVENT_Y'].between(21, 79))).sum()),
        Gennembrud=('EVENT_TYPEID', lambda x: ((df_input.loc[x.index, 'EVENT_TYPEID'] == 1) & 
                                               (df_input.loc[x.index, 'EVENT_X'] > 70)).sum()),
        Dueller=('EVENT_TYPEID', lambda x: x.isin([7, 44]).sum()),
        Chancer=('qual_list', lambda x: x.apply(lambda q: '210' in q or '209' in q).sum())
    ).reset_index()

    # Lav en simpel vægtet score for at finde de 5 "vigtigste"
    stats['Score'] = (stats['Touches_Box'] * 3) + (stats['Gennembrud'] * 1.5) + (stats['Chancer'] * 2)
    top_5 = stats.sort_values('Score', ascending=False).head(5)

    # 2. VISNING (5 Kolonner)
    cols = st.columns(5)
    
    # Farver til de forskellige bars
    farver = ["#df003b", "#084594", "#238b45", "#ec7014"]

    for i, (idx, row) in enumerate(top_5.iterrows()):
        with cols[i]:
            # Navn med stor skrift
            st.markdown(f"**{row['PLAYER_NAME'].split()[-1].upper()}**")
            st.caption(row['PLAYER_NAME'])
            
            # En placeholder linje
            st.markdown("<hr style='margin:10px 0; border:1px solid #eee'>", unsafe_allow_html=True)
            
            # Funktion til de visuelle bjælker
            def draw_bar(label, val, max_val, color):
                percent = min(int((val / max_val) * 100), 100) if max_val > 0 else 0
                st.markdown(f"""
                    <div style="font-size: 10px; color: #666; margin-top: 8px;">{label}</div>
                    <div style="background-color: #f1f1f1; border-radius: 3px; height: 6px; width: 100%;">
                        <div style="background-color: {color}; height: 6px; width: {percent}%; border-radius: 3px;"></div>
                    </div>
                    <div style="font-size: 10px; font-weight: bold; text-align: right;">{int(val)}</div>
                """, unsafe_allow_html=True)

            # Tegn metrics
            draw_bar("TOUCHES IN BOX", row['Touches_Box'], stats['Touches_Box'].max(), farver[0])
            draw_bar("GENNEMBRUD", row['Gennembrud'], stats['Gennembrud'].max(), farver[1])
            draw_bar("DUELLER", row['Dueller'], stats['Dueller'].max(), farver[2])
            draw_bar("CHANCE SKABT", row['Chancer'], stats['Chancer'].max(), farver[3])

# KALD FUNKTIONEN MED DIT RIGTIGE DATAFRAME
vis_side(df_all_h)
