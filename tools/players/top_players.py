import streamlit as st
import pandas as pd

def vis_side(df_modstander):
    st.header("PHYSICAL & TECHNICAL PROFILES")
    st.subheader(f"Top 5 profiler hos {valgt_hold}")

    # 1. FIND DE 5 MEST ORIGINALE/FARLIGE SPILLERE
    # Vi kigger på en kombination af volumen og effektivitet
    player_impact = df_modstander.groupby('PLAYER_NAME').agg(
        Touches_i_felt=('EVENT_X', lambda x: ((df_modstander.loc[x.index, 'EVENT_X'] > 83) & 
                                              (df_modstander.loc[x.index, 'EVENT_Y'].between(21, 79))).sum()),
        Gennembrud=('EVENT_TYPEID', lambda x: (x == 1).sum()), # Her kan du tilføje filter for X > 70
        Dueller_Vundne=('OUTCOME', lambda x: ((df_modstander.loc[x.index, 'EVENT_TYPEID'].isin([7, 44])) & (x == 1)).sum()),
        Skud=('EVENT_TYPEID', lambda x: x.isin([13, 14, 15, 16]).sum())
    ).reset_index()

    # Vi rater dem efter en simpel score for at finde profilerne
    player_impact['Score'] = player_impact['Touches_i_felt'] * 2 + player_impact['Gennembrud'] + player_impact['Dueller_Vundne']
    top_5_spillere = player_impact.sort_values('Score', ascending=False).head(5)

    # 2. VISNING I KOLONNER (Ligesom dit billede)
    cols = st.columns(5)
    
    for i, (idx, row) in enumerate(top_5_spillere.iterrows()):
        with cols[i]:
            # Placeholder for billede - du kan linke til spillernes rigtige billeder hvis du har URL'er
            st.image("https://via.placeholder.com/150/df003b/ffffff?text=" + row['PLAYER_NAME'].split()[-1], use_container_width=True)
            st.markdown(f"**{row['PLAYER_NAME']}**", help="Baseret på seneste 10 kampe")
            
            # Lav de vandrette barer (Volume Metrics)
            st.write("---")
            
            # Funktion til at lave en lille bar
            def metric_bar(label, value, max_val, color="#ff4b4b"):
                percent = min(int((value / max_val) * 100), 100) if max_val > 0 else 0
                st.markdown(f"""
                    <div style="font-size: 10px; margin-bottom: -5px;">{label}</div>
                    <div style="background-color: #f0f2f6; border-radius: 2px; height: 8px; width: 100%;">
                        <div style="background-color: {color}; height: 8px; width: {percent}%; border-radius: 2px;"></div>
                    </div>
                    <div style="font-size: 10px; text-align: right; margin-top: 2px;">{int(value)}</div>
                """, unsafe_allow_html=True)

            # Eksempler på metrics pr. spiller
            metric_bar("Touches in Box", row['Touches_i_felt'], player_impact['Touches_i_felt'].max())
            metric_bar("Gennembrud", row['Gennembrud'], player_impact['Gennembrud'].max(), color="#084594")
            metric_bar("Vundne Dueller", row['Dueller_Vundne'], player_impact['Dueller_Vundne'].max(), color="#238b45")
            metric_bar("Skud", row['Skud'], player_impact['Skud'].max(), color="#ec7014")

    st.markdown("---")
    st.info("Denne oversigt viser de 5 spillere, der statistisk set har den største indflydelse på modstanderens spil i den sidste tredjedel.")

# Kald funktionen på din nye side:
# vis_spiller_profiler(df_all_h)
