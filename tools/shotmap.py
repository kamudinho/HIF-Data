import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 10px 15px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 8px; }
            .stat-label { font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }
            .stat-value { font-size: 1.6rem; font-weight: 800; color: #1a1a1a; margin-left: 5px; }
        </style>
    """, unsafe_allow_html=True)
    
    # 1. Sikker hentning af data
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    df_assists = dp.get('assists', pd.DataFrame()) 
    df_quals = dp.get('qualifiers', pd.DataFrame())
    
    # Præ-processering af Danger Zone (Q16 og Q17)
    if not df_skud.empty and not df_quals.empty:
        danger_ids = [16, 17, '16', '17']
        dz_events = df_quals[df_quals['QUALIFIER_QID'].isin(danger_ids)]['EVENT_OPTAUUID'].unique()
        df_skud['IS_DZ'] = df_skud['EVENT_OPTAUUID'].isin(dz_events)
    else:
        df_skud['IS_DZ'] = False

    tab1, tab2, tab3 = st.tabs(["AFSLUTNINGER", "ASSISTS", "DANGER ZONE ANALYSE"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        if df_skud.empty:
            st.info("Ingen skuddata fundet.")
        else:
            col_viz, col_ctrl = st.columns([3, 1])
            with col_ctrl:
                spiller_liste = sorted(df_skud['PLAYER_NAME'].unique())
                v_skud = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_skud")
                df_vis = df_skud if v_skud == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
                
                st.markdown(f'<div class="stat-box"><div class="stat-label">Skud i alt</div><div class="stat-value">{len(df_vis)}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(df_vis[df_vis["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)

            with col_viz:
                pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig, ax = pitch.draw(figsize=(8, 10))
                c_map = (df_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=150, c=c_map, edgecolors=HIF_RED, ax=ax)
                st.pyplot(fig)

    # --- TAB 2: ASSISTS (Uændret) ---
    with tab2:
        # ... din eksisterende assist logik ...
        if not df_assists.empty:
             # (Indsæt din eksisterende kode her for at bevare funktionalitet)
             pass

    # --- TAB 3: DANGER ZONE ANALYSE ---
    with tab3:
        if df_skud.empty:
            st.info("Ingen data til DZ analyse.")
        else:
            col_dz_viz, col_dz_ctrl = st.columns([3, 1])
            
            # Filter til DZ tab
            spiller_liste_dz = sorted(df_skud['PLAYER_NAME'].unique())
            v_dz = col_dz_ctrl.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste_dz, key="sb_dz")
            df_dz_vis = df_skud if v_dz == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_dz]
            
            dz_hits = df_dz_vis[df_dz_vis['IS_DZ']]
            non_dz_hits = df_dz_vis[~df_dz_vis['IS_DZ']]
            
            with col_dz_ctrl:
                st.markdown(f'<div class="stat-box" style="border-left-color: {DZ_COLOR}"><div class="stat-label">Danger Zone Skud</div><div class="stat-value">{len(dz_hits)}</div></div>', unsafe_allow_html=True)
                
                # Beregn konverteringsrate i DZ
                if len(dz_hits) > 0:
                    goals_dz = len(dz_hits[dz_hits['EVENT_TYPEID'] == 16])
                    conv_rate = (goals_dz / len(dz_hits)) * 100
                    st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Mål / Rate</div><div class="stat-value">{goals_dz} ({conv_rate:.0f}%)</div></div>', unsafe_allow_html=True)

            with col_dz_viz:
                pitch_dz = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig_dz, ax_dz = pitch_dz.draw(figsize=(8, 10))
                
                # Markér Danger Zone tydeligt
                pitch_dz.box(x_mid=94.25, y_mid=50, width=11.5, height=26, 
                             ax=ax_dz, color=DZ_COLOR, alpha=0.2, linestyle='--', linewidth=3)
                
                # Plot kun Danger Zone skud med farve, og ton de andre ud
                pitch_dz.scatter(dz_hits['EVENT_X'], dz_hits['EVENT_Y'], s=200, 
                                 c=HIF_RED, edgecolors='black', label='I Danger Zone', ax=ax_dz, zorder=3)
                
                pitch_dz.scatter(non_dz_hits['EVENT_X'], non_dz_hits['EVENT_Y'], s=80, 
                                 c='white', edgecolors='#cccccc', alpha=0.3, label='Udenfor DZ', ax=ax_dz, zorder=2)
                
                ax_dz.legend(loc='lower center', ncol=2)
                st.pyplot(fig_dz)

            # Ekstra indsigt: Tabel over DZ afslutninger
            if not dz_hits.empty:
                st.write("---")
                st.subheader("Oversigt over Danger Zone afslutninger")
                dz_table = dz_hits[['PLAYER_NAME', 'EVENT_TIMEMIN', 'EVENT_TYPEID', 'XG_RAW']].copy()
                dz_table['Resultat'] = dz_table['EVENT_TYPEID'].map({16: 'MÅL'}).fillna('Ikke mål')
                st.dataframe(dz_table[['PLAYER_NAME', 'EVENT_TIMEMIN', 'Resultat', 'XG_RAW']], use_container_width=True, hide_index=True)
