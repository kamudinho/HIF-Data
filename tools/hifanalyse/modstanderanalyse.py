import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package=None):
    # --- 1. UI & CSS ---
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem; }
            .stat-box { 
                background-color: #f8f9fa; padding: 8px; border-radius: 6px; 
                border-left: 4px solid #df003b; margin-bottom: 5px; font-size: 0.85rem;
            }
            .pitch-label { text-align: center; font-weight: bold; font-size: 14px; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    if analysis_package is None:
        st.error("Datapakken blev ikke fundet. Sørg for at 'get_analysis_package()' kaldes korrekt.")
        return

    # --- 2. DATA-LOAD FRA PAKKEN ---
    # Vi henter matches for at få holdnavne og UUIDs
    df_matches = analysis_package.get("matches", pd.DataFrame())
    # Vi henter shapes til Tab 0
    df_shapes = analysis_package.get("shapes", pd.DataFrame())
    # Vi henter de rå events (Query 8) til Tab 1, 2 og 3
    df_all_events = analysis_package.get("opta", {}).get("opta_events", pd.DataFrame())

    if df_matches.empty:
        st.warning("Ingen kampdata fundet i pakken.")
        return

    # --- 3. FILTER-RÆKKE ---
    col_h1, col_h2, _ = st.columns([1, 1, 2])
    
    with col_h1:
        # Vi tager alle unikke holdnavne fra kampskemaet
        hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique())
        valgt_hold = st.selectbox("Vælg hold:", hold_navne)
    
    # Find UUID for det valgte hold
    hold_uuid = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]['CONTESTANTHOME_OPTAUUID'].iloc[0]
    
    # Filtrér data specifikt til dette hold
    df_hold = df_all_events[df_all_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()
    df_shape_hold = df_shapes[df_shapes['CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    with col_h2:
        # Spillerfilter baseret på de events vi har fundet
        spiller_liste = ["Alle spillere"]
        if 'PLAYER_NAME' in df_hold.columns:
            spiller_liste += sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Filter spiller:", spiller_liste)

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # --- 4. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # TAB 0: GRUNDSTRUKTUR
    with tabs[0]:
        st.markdown(f"#### Taktisk udgangspunkt: {valgt_hold}")
        if not df_shape_hold.empty:
            meste_brugte = df_shape_hold['SHAPE_FORMATION'].value_counts().idxmax()
            avg_xg = df_shape_hold['SHAPEOUTCOME_XG'].mean()
            
            c1, c2 = st.columns(2)
            c1.metric("Foretrukken formation", meste_brugte)
            c2.metric("Gns. xG pr. kamp", f"{avg_xg:.2f}")
            
            st.write("Seneste benyttede formationer (Shape Data):")
            st.dataframe(df_shape_hold[['SHAPE_LABEL', 'SHAPE_FORMATION', 'SHAPEOUTCOME_XG']].tail(5), use_container_width=True)
        else:
            st.info("Ingen taktisk shape-data fundet for dette hold.")

    # TAB 1: MED BOLD
    with tabs[1]:
        c1, c2 = st.columns(2)
        pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        
        # Opbygning (Passes i egen halvleg)
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING (Egne 50m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
            df_p = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] < 50)]
            if not df_p.empty: 
                sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap='Reds', ax=ax, clip=((0,100),(0,50)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)
            
        # Gennembrud (Passes i modstanders halvleg)
        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD (Sidste 50m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
            df_g = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] >= 50)]
            if not df_g.empty: 
                sns.kdeplot(x=df_g['LOCATIONY'], y=df_g['LOCATIONX'], fill=True, cmap='Reds', ax=ax, clip=((0,100),(50,100)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)

    # TAB 2: MOD BOLD
    with tabs[2]:
        st.markdown('<p class="pitch-label">DEFENSIV INTENSITET (Tacklinger, Erobringer & Dueller)</p>', unsafe_allow_html=True)
        pitch_f = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
        fig, ax = pitch_f.draw(figsize=(4, 6))
        
        # Vi filtrerer på de defensive TypeIDs fra din Query 8
        df_d = df_hold[df_hold['EVENT_TYPEID'].isin([4, 5, 8, 49])]
        
        if not df_d.empty: 
            sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap='Blues', ax=ax, clip=((0,100),(0,100)))
        else:
            st.warning("Ingen defensive aktioner fundet i de hentede data.")
        st.pyplot(fig, use_container_width=True); plt.close(fig)

    # TAB 3: TOP 5
    with tabs[3]:
        cols = st.columns(3)
        # Kategorier baseret på dine SQL-typer
        for i, (tid, nav) in enumerate([([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]):
            with cols[i]:
                st.markdown(f"**Top {nav}**")
                if 'PLAYER_NAME' in df_hold.columns:
                    top = df_hold[df_hold['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                    for n, c in top.items(): 
                        st.markdown(f'<div class="stat-box"><b>{c}</b> {n}</div>', unsafe_allow_html=True)
                else:
                    st.write("Ingen spillernavne tilgængelige.")

if __name__ == "__main__":
    # Dette er kun til lokal test - i produktion kaldes vis_side fra din main-app
    vis_side()
