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

    if not analysis_package:
        st.error("Ingen datapakke fundet.")
        return

    # --- 2. DATA-UDTRÆK ---
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_shapes = analysis_package.get("shapes", pd.DataFrame())
    # Vi henter rå events fra 'opta' sub-dictionary
    df_all_events = analysis_package.get("opta", {}).get("opta_events", pd.DataFrame())

    if df_matches.empty:
        st.warning("Ingen kampdata tilgængelig.")
        return

    # --- 3. FILTER-SEKTION ---
    col_h1, col_h2, _ = st.columns([1, 1, 2])
    with col_h1:
        hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique())
        valgt_hold = st.selectbox("Vælg hold:", hold_navne)
    
    # Hent UUID (Vi bruger kolonnenavnet fra din OPTA_MATCHINFO query)
    hold_uuid = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]['CONTESTANTHOME_OPTAUUID'].iloc[0]

    # SIKKERHEDS-CHECK: Find den rigtige kolonne til hold-ID i event-data
    # Din Query 8 bruger 'EVENT_CONTESTANT_OPTAUUID'
    col_id = 'EVENT_CONTESTANT_OPTAUUID' 
    if col_id not in df_all_events.columns:
        # Hvis Snowflake har ændret case eller alias
        possible_cols = [c for c in df_all_events.columns if 'CONTESTANT' in c and 'UUID' in c]
        col_id = possible_cols[0] if possible_cols else None

    if not col_id or df_all_events.empty:
        st.error(f"Kunne ikke finde kolonnen '{col_id}' i event-data. Tjek din SQL Query 8.")
        return

    # Filtrér data
    df_hold = df_all_events[df_all_events[col_id] == hold_uuid].copy()
    df_shape_hold = df_shapes[df_shapes['CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    with col_h2:
        spiller_cols = [c for c in df_hold.columns if 'PLAYER_NAME' in c]
        s_col = spiller_cols[0] if spiller_cols else None
        spillere = ["Alle spillere"]
        if s_col:
            spillere += sorted(df_hold[s_col].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Filter spiller:", spillere)

    if valgt_spiller != "Alle spillere" and s_col:
        df_hold = df_hold[df_hold[s_col] == valgt_spiller]

    # --- 4. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # TAB 0: SHAPE
    with tabs[0]:
        st.subheader(f"Taktisk Struktur: {valgt_hold}")
        if not df_shape_hold.empty:
            meste_brugte = df_shape_hold['SHAPE_FORMATION'].value_counts().idxmax()
            c1, c2 = st.columns(2)
            c1.metric("Primær Formation", meste_brugte)
            c2.metric("Gns. xG", f"{df_shape_hold['SHAPEOUTCOME_XG'].mean():.2f}")
            st.table(df_shape_hold[['SHAPE_LABEL', 'SHAPE_FORMATION', 'SHAPEOUTCOME_XG']].tail(5))
        else:
            st.info("Ingen shape-data fundet for dette hold.")

    # TAB 1: MED BOLD
    with tabs[1]:
        c1, c2 = st.columns(2)
        pitch = VerticalPitch(pitch_type='opta', half=True, line_color='#333333')
        
        # LOCATIONX og LOCATIONY er aliaser fra din Query 8
        with c1:
            st.write("**Opbygning**")
            fig, ax = pitch.draw(); ax.set_ylim(0, 50)
            d = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] < 50)]
            if not d.empty: sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Reds', ax=ax)
            st.pyplot(fig); plt.close(fig)
        with c2:
            st.write("**Gennembrud**")
            fig, ax = pitch.draw(); ax.set_ylim(50, 100)
            d = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] >= 50)]
            if not d.empty: sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Reds', ax=ax)
            st.pyplot(fig); plt.close(fig)

    # TAB 2: MOD BOLD
    with tabs[2]:
        st.write("**Defensiv Positionering**")
        pitch_f = VerticalPitch(pitch_type='opta', line_color='#333333')
        fig, ax = pitch_f.draw()
        d = df_hold[df_hold['EVENT_TYPEID'].isin([4, 5, 8, 49])]
        if not d.empty: sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Blues', ax=ax)
        st.pyplot(fig); plt.close(fig)

    # TAB 3: TOP 5
    with tabs[3]:
        c = st.columns(3)
        maps = [([1], 'Passes'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
        for i, (ids, txt) in enumerate(maps):
            with c[i]:
                st.write(f"**{txt}**")
                if s_col:
                    t = df_hold[df_hold['EVENT_TYPEID'].isin(ids)][s_col].value_counts().head(5)
                    for n, val in t.items(): st.markdown(f'<div class="stat-box"><b>{val}</b> {n}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
