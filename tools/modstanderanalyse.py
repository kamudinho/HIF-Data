import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
# Vigtigt: Sørg for at denne import er her
from data.data_load import load_snowflake_query

def vis_side(df_team_matches, hold_map, df_events=None):
    st.markdown('<div class="custom-header"><h3>Modstanderanalyse</h3></div>', unsafe_allow_html=True)

    # --- AUTOMATISK DATA INDLÆSNING ---
    # Vi tjekker om vi allerede har data. Hvis ikke, henter vi det uden at spørge.
    if "events_data" not in st.session_state:
        with st.spinner("Indlæser detaljeret kamp-data automatisk..."):
            dp = st.session_state["data_package"]
            st.session_state["events_data"] = load_snowflake_query(
                "events", dp["comp_filter"], dp["season_filter"]
            )
            # Vi tvinger et rerun så 'df_events' variablen bliver fyldt med det samme
            st.rerun()

    # Nu kan vi med sikkerhed bruge data fra session_state
    df_events = st.session_state["events_data"]
        
    # --- 1. CSS STYLING ---
    st.markdown("""
        <style>
            [data-testid="stMetric"] {
                background-color: #ffffff; padding: 15px; border-radius: 10px; 
                border-bottom: 4px solid #cc0000; box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DROPDOWNS OG FILTRERING ---
    if 'COMPETITION_NAME' in df_team_matches.columns:
        comp_options = df_team_matches[['COMPETITION_NAME', 'COMPETITION_WYID']].drop_duplicates()
        comp_dict = dict(zip(comp_options['COMPETITION_NAME'], comp_options['COMPETITION_WYID']))
        
        col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])
        with col_sel1:
            valgt_comp_navn = st.selectbox("Vælg Turnering:", options=sorted(comp_dict.keys()))
            valgt_comp_id = comp_dict[valgt_comp_navn]
    else:
        turneringer = sorted(df_team_matches['COMPETITION_WYID'].unique())
        col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])
        with col_sel1:
            valgt_comp_id = st.selectbox("Vælg Turnering (ID):", options=turneringer)

    # Filtrer hold baseret på turnering
    df_filtered_comp = df_team_matches[df_team_matches['COMPETITION_WYID'] == valgt_comp_id]
    
    # Lav navne_dict
    navne_dict = {}
    for tid in df_filtered_comp['TEAM_WYID'].unique():
        # Hvis det er et tal (Wyscout), konverter til int. 
        # Hvis det er en tekst (Opta), behold det som str.
        try:
            lookup_id = int(float(tid)) if str(tid).replace('.','').isdigit() else str(tid)
            navn = hold_map.get(lookup_id, f"Hold {tid}")
            navne_dict[navn] = tid
        except:
            navne_dict[f"Ukendt {tid}"] = tid
    
    with col_sel2:
        valgt_hold_navn = st.selectbox("Vælg Modstander:", options=sorted(navne_dict.keys()))
        valgt_hold_id = navne_dict[valgt_hold_navn]
        
    with col_sel3:
        halvdel = st.radio("Fokus:", ["Modstander", "Egen"], horizontal=True)

    df_hold_data = df_filtered_comp[df_filtered_comp['TEAM_WYID'] == valgt_hold_id].copy()

    # --- 3. STATISTISK OVERBLIK ---
    st.subheader(f"Statistisk overblik: {valgt_hold_navn}")
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.metric("GNS. MÅL", round(df_hold_data['GOALS'].mean(), 1) if 'GOALS' in df_hold_data else 0.0)
    with m2:
        st.metric("GNS. XG", round(df_hold_data['XG'].mean(), 2) if 'XG' in df_hold_data else 0.0)
    with m3:
        st.metric("SKUD PR. KAMP", round(df_hold_data['SHOTS'].mean(), 1) if 'SHOTS' in df_hold_data else 0.0)
    with m4:
        st.metric("SKUD PÅ MÅL", round(df_hold_data['SHOTSONTARGET'].mean(), 1) if 'SHOTSONTARGET' in df_hold_data else 0.0)

    st.markdown("---")

    # --- 4. HEATMAPS OG KAMP-LISTE ---
    main_col, side_col = st.columns([3, 1])

    with main_col:
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#333', half=True)
        c1, c2, c3 = st.columns(3)
        
        target_id_str = str(int(valgt_hold_id))
        
        # Filtrering af events
        df_hold_ev = df_events[df_events['TEAM_WYID'].astype(str).str.contains(target_id_str)].copy()

        if not df_hold_ev.empty:
            if halvdel == "Modstander":
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50]
            else:
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

            plots = [
                (c1, "Afleveringer", "pass", "Reds"), 
                (c2, "Dueller", "duel", "Blues"), 
                (c3, "Erobringer", "interception", "Greens")
            ]
            
            for col, title, p_type, cmap in plots:
                with col:
                    st.write(f"**{title}**")
                    fig, ax = pitch.draw(figsize=(4, 5))
                    mask = df_plot['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)
                    df_f = df_plot[mask]
                    
                    if not df_f.empty:
                        sns.kdeplot(
                            x=df_f['LOCATIONY'], y=df_f['LOCATIONX'], ax=ax, 
                            fill=True, cmap=cmap, alpha=0.7, levels=10,
                            thresh=0.05, clip=((0, 100), (50, 100))
                        )
                        ax.set_xlim(0, 100)
                        ax.set_ylim(50, 100)
                    else:
                        ax.text(50, 75, "Ingen data", ha='center', va='center', color='gray')
                    st.pyplot(fig, use_container_width=True)
        else:
            st.warning(f"Ingen hændelsesdata fundet for {valgt_hold_navn}")

    with side_col:
        st.write("**Seneste kampe**")
        if not df_hold_data.empty:
            # 1. Lav en kopi og konverter til datetime for korrekt sortering
            df_display = df_hold_data.copy()
            df_display['DATE'] = pd.to_datetime(df_display['DATE'])
            
            # 2. Sortér EFTER datoen (nyeste øverst) FØR vi laver det om til tekst
            df_display = df_display.sort_values('DATE', ascending=False)
            
            # 3. Formater Dato til DD-MM-YY streng
            df_display['DATE_STR'] = df_display['DATE'].dt.strftime('%d-%m-%y')
            
            # 4. Rens MATCHLABEL: Erstat ',' med ' - ' og fjern overflødige 'vs.' hvis de driller
            if 'MATCHLABEL' in df_display.columns:
                # Vi fjerner kommaet og indsætter en pæn separator
                df_display['MATCHLABEL'] = df_display['MATCHLABEL'].str.replace(r',', ' -', regex=True)

            # 5. Vælg kolonner og omdøb for visning
            # Vi bruger 'DATE_STR' til visning, men holdt 'DATE' til sortering
            df_final = df_display[['DATE_STR', 'MATCHLABEL']].rename(columns={'DATE_STR': 'DATO', 'MATCHLABEL': 'KAMP'})
            
            st.dataframe(
                df_final, 
                hide_index=True,
                use_container_width=True
            )
