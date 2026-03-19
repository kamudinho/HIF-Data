import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package=None):
    # --- 1. Layout: Titel og Dropdowns på samme linje ---
    col_titel, col_h1, col_h2 = st.columns([2, 1, 1])
    
    with col_titel:
        st.subheader("MODSTANDERANALYSE")

    if not analysis_package:
        st.error("Fejl: Ingen datapakke fundet.")
        return

    # Hent data
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_shapes = analysis_package.get("shapes", pd.DataFrame())
    df_all_events = analysis_package.get("opta", {}).get("opta_events", pd.DataFrame())

    if df_all_events.empty:
        st.error("Data-fejl: 'opta_events' er tom. Tjek din analyse_load.py")
        return

    # --- 2. Dropdowns i kolonnerne til højre ---
    with col_h1:
        hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique())
        valgt_hold = st.selectbox("Vælg hold", hold_navne, label_visibility="collapsed")
    
    # Find UUID
    hold_uuid = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]['CONTESTANTHOME_OPTAUUID'].iloc[0]
    
    # Forbered event-data (Upper case kolonner for sikkerhed)
    df_all_events.columns = [c.upper() for c in df_all_events.columns]
    col_team = 'EVENT_CONTESTANT_OPTAUUID'
    col_player = 'PLAYER_NAME'
    
    # Filtrér primært på holdet med det samme
    df_hold = df_all_events[df_all_events[col_team] == hold_uuid].copy()

    with col_h2:
        spillere = ["Alle spillere"] + sorted(df_hold[col_player].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", spillere, label_visibility="collapsed")

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold[col_player] == valgt_spiller]

    # --- 3. Tabs ---
    tabs = st.tabs(["📊 GRUNDSTRUKTUR", "⚽ MED BOLD", "🛡️ MOD BOLD", "🏆 TOP 5"])

    # TAB 0: GRUNDSTRUKTUR
    with tabs[0]:
        df_shape_hold = df_shapes[df_shapes['CONTESTANT_OPTAUUID'] == hold_uuid].copy() if not df_shapes.empty else pd.DataFrame()
        if not df_shape_hold.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Primær Formation", df_shape_hold['SHAPE_FORMATION'].value_counts().idxmax())
            with c2:
                avg_xg = df_shape_hold['SHAPEOUTCOME_XG'].mean()
                st.metric("Gns. xG", f"{avg_xg:.2f}")
            
            st.write("**Seneste kampe (Formationer)**")
            st.dataframe(df_shape_hold[['SHAPE_LABEL', 'SHAPE_FORMATION', 'SHAPEOUTCOME_XG']].tail(5), use_container_width=True)
        else:
            st.info("Ingen shape-data fundet for dette hold.")

    # TAB 1: MED BOLD
    with tabs[1]:
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        c1, c2 = st.columns(2)
        
        # Opbygning
        with c1:
            st.markdown("<center><b>Opbygning (Egen Halvdel)</b></center>", unsafe_allow_html=True)
            fig, ax = pitch.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
            d = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] < 50)]
            if not d.empty: 
                sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Reds', ax=ax, alpha=0.7, thresh=0.1)
            st.pyplot(fig, use_container_width=True); plt.close(fig)
            
        # Gennembrud
        with c2:
            st.markdown("<center><b>Gennembrud (Modstanders Halvdel)</b></center>", unsafe_allow_html=True)
            fig, ax = pitch.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
            d = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] >= 50)]
            if not d.empty: 
                sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Reds', ax=ax, alpha=0.7, thresh=0.1)
            st.pyplot(fig, use_container_width=True); plt.close(fig)

    # TAB 2: MOD BOLD
    with tabs[2]:
        st.markdown("<center><b>Defensiv Struktur (Tacklinger, Erobringer, Dueller)</b></center>", unsafe_allow_html=True)
        pitch_f = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
        fig, ax = pitch_f.draw(figsize=(6, 10))
        
        # Typer: 4=Tackle, 5=Duel, 8=Interception, 49=Recovery
        d = df_hold[df_hold['EVENT_TYPEID'].isin([4, 5, 8, 49])]
        if not d.empty: 
            sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Blues', ax=ax, alpha=0.7, thresh=0.1)
        st.pyplot(fig, use_container_width=True); plt.close(fig)

    # TAB 3: TOP 5
    with tabs[3]:
        st.write("**Top-præstationer (Valgt hold/spiller)**")
        c = st.columns(3)
        stats = [([1], 'Afleveringer'), ([4, 5], 'Dueller'), ([8, 49], 'Erobringer')]
        
        for i, (ids, txt) in enumerate(stats):
            with c[i]:
                st.subheader(txt)
                t = df_hold[df_hold['EVENT_TYPEID'].isin(ids)][col_player].value_counts().head(5)
                if not t.empty:
                    for n, v in t.items():
                        st.markdown(f"**{v}** {n}")
                else:
                    st.write("Ingen data")
