import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package=None):
    # --- 1. TOP BAR (Titel og Dropdowns på én linje) ---
    st.markdown("<style>div[data-testid='stHorizontalBlock'] { align-items: center; }</style>", unsafe_allow_html=True)
    
    hdr_col1, hdr_col2, hdr_col3 = st.columns([2, 1, 1])
    
    with hdr_col1:
        st.subheader("BETINIA LIGAEN | ANALYSE")

    if not analysis_package:
        st.error("Ingen datapakke fundet.")
        return

    # Hent grunddata
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_shapes = analysis_package.get("shapes", pd.DataFrame())
    # Hent events fra 'opta' sub-dict
    opta_data = analysis_package.get("opta", {})
    df_all_events = opta_data.get("opta_events", pd.DataFrame())

    # Dropdowns i de to små kolonner til højre
    with hdr_col2:
        hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique()) if not df_matches.empty else []
        valgt_hold = st.selectbox("Vælg hold", hold_navne, label_visibility="collapsed")
    
    # Find UUID for det valgte hold
    hold_uuid = ""
    if not df_matches.empty and valgt_hold:
        match_row = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]
        if not match_row.empty:
            hold_uuid = match_row['CONTESTANTHOME_OPTAUUID'].iloc[0]

    # Præ-filtrér events for det valgte hold
    df_hold = pd.DataFrame()
    if not df_all_events.empty and hold_uuid:
        df_all_events.columns = [c.upper() for c in df_all_events.columns]
        df_hold = df_all_events[df_all_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    with hdr_col3:
        spiller_liste = ["Alle spillere"]
        if not df_hold.empty:
            spiller_liste += sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", spiller_liste, label_visibility="collapsed")

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # --- 2. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # TAB 0: SHAPES (GRUNDSTRUKTUR)
    with tabs[0]:
        if not df_shapes.empty and hold_uuid:
            # Vi filtrerer shapes på holdets UUID
            df_s = df_shapes[df_shapes['CONTESTANT_OPTAUUID'] == hold_uuid].copy()
            if not df_s.empty:
                c1, c2 = st.columns(2)
                c1.metric("Mest brugte formation", df_s['SHAPE_FORMATION'].value_counts().idxmax())
                c2.metric("Gns. xG (Open Play)", f"{df_s['SHAPEOUTCOME_XG'].mean():.2f}")
                
                st.write("**Seneste taktikker:**")
                st.dataframe(df_s[['SHAPE_LABEL', 'SHAPE_FORMATION', 'SHAPEOUTCOME_XG']].tail(5), use_container_width=True)
            else:
                st.info(f"Ingen taktisk data fundet for {valgt_hold} i denne turnering.")
        else:
            st.warning("Shape-data er ikke indlæst korrekt i analyse_load.py")

    # TAB 1: MED BOLD
    with tabs[1]:
        if df_hold.empty:
            st.info("Ingen event-data tilgængelig for dette hold.")
        else:
            pitch = VerticalPitch(pitch_type='opta', half=True, line_color='#333333')
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Opbygning (0-50m)**")
                fig, ax = pitch.draw(); ax.set_ylim(0, 50)
                d = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] < 50)]
                if not d.empty: sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Reds', ax=ax)
                st.pyplot(fig); plt.close(fig)
            with c2:
                st.write("**Gennembrud (50-100m)**")
                fig, ax = pitch.draw(); ax.set_ylim(50, 100)
                d = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] >= 50)]
                if not d.empty: sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Reds', ax=ax)
                st.pyplot(fig); plt.close(fig)

    # TAB 2: MOD BOLD
    with tabs[2]:
        if not df_hold.empty:
            pitch_f = VerticalPitch(pitch_type='opta', line_color='#333333')
            fig, ax = pitch_f.draw()
            # 4=Tackle, 5=Duel, 8=Interception, 49=Recovery
            d = df_hold[df_hold['EVENT_TYPEID'].isin([4, 5, 8, 49])]
            if not d.empty: sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Blues', ax=ax)
            st.pyplot(fig); plt.close(fig)

    # TAB 3: TOP 5
    with tabs[3]:
        if not df_hold.empty:
            c = st.columns(3)
            cats = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
            for i, (ids, txt) in enumerate(cats):
                with c[i]:
                    st.write(f"**{txt}**")
                    t = df_hold[df_hold['EVENT_TYPEID'].isin(ids)]['PLAYER_NAME'].value_counts().head(5)
                    for n, v in t.items(): st.markdown(f"**{v}** {n}")
