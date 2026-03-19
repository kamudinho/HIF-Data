import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package=None):
    st.title("MODSTANDERANALYSE")

    if not analysis_package:
        st.error("Fejl: Ingen datapakke modtaget fra analyse_load.py")
        return

    # 1. Hent data
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_shapes = analysis_package.get("shapes", pd.DataFrame())
    # Vi henter fra 'opta' sub-dictionary
    df_all_events = analysis_package.get("opta", {}).get("opta_events", pd.DataFrame())

    # --- DEBUG SEKTION (Fjern denne når det virker) ---
    if df_all_events.empty:
        st.error("Data-fejl: 'opta_events' er tom. Tjek Query 8 i opta_queries.py")
        return
    # --------------------------------------------------

    # 2. Vælg hold
    hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique())
    valgt_hold = st.selectbox("Vælg hold:", hold_navne)
    
    # Hent holdets UUID fra match-tabellen
    hold_uuid = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]['CONTESTANTHOME_OPTAUUID'].iloc[0]

    # 3. FILTRERING MED SIKKERHEDSNET
    # Vi tvinger kolonnerne til upper-case for at undgå små/store bogstaver fejl fra Snowflake
    df_all_events.columns = [c.upper() for c in df_all_events.columns]
    
    col_team = 'EVENT_CONTESTANT_OPTAUUID'
    col_player = 'PLAYER_NAME'

    if col_team not in df_all_events.columns:
        st.error(f"Kolonnen '{col_team}' mangler! Tilgængelige kolonner: {list(df_all_events.columns)}")
        return

    # Nu filtrerer vi
    df_hold = df_all_events[df_all_events[col_team] == hold_uuid].copy()
    df_shape_hold = df_shapes[df_shapes['CONTESTANT_OPTAUUID'] == hold_uuid].copy() if not df_shapes.empty else pd.DataFrame()

    # 4. Spiller filter
    valgt_spiller = st.selectbox("Filter spiller:", ["Alle spillere"] + sorted(df_hold[col_player].dropna().unique().tolist()))
    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold[col_player] == valgt_spiller]

    # 5. TABS
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # SHAPE
        if not df_shape_hold.empty:
            st.metric("Primær Formation", df_shape_hold['SHAPE_FORMATION'].value_counts().idxmax())
            st.dataframe(df_shape_hold[['SHAPE_LABEL', 'SHAPE_FORMATION', 'SHAPEOUTCOME_XG']].tail(5))
        else:
            st.info("Ingen shape-data fundet.")

    with tabs[1]: # MED BOLD
        pitch = VerticalPitch(pitch_type='opta', half=True, line_color='#333333')
        c1, c2 = st.columns(2)
        # Opbygning
        with c1:
            fig, ax = pitch.draw(); ax.set_ylim(0, 50)
            d = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] < 50)]
            if not d.empty: sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Reds', ax=ax)
            st.pyplot(fig); plt.close(fig)
        # Gennembrud
        with c2:
            fig, ax = pitch.draw(); ax.set_ylim(50, 100)
            d = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] >= 50)]
            if not d.empty: sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Reds', ax=ax)
            st.pyplot(fig); plt.close(fig)

    with tabs[2]: # MOD BOLD
        pitch_f = VerticalPitch(pitch_type='opta', line_color='#333333')
        fig, ax = pitch_f.draw()
        d = df_hold[df_hold['EVENT_TYPEID'].isin([4, 5, 8, 49])]
        if not d.empty: sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, cmap='Blues', ax=ax)
        st.pyplot(fig); plt.close(fig)

    with tabs[3]: # TOP 5
        c = st.columns(3)
        for i, (ids, txt) in enumerate([([1], 'Passes'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]):
            with c[i]:
                st.write(f"**{txt}**")
                t = df_hold[df_hold['EVENT_TYPEID'].isin(ids)][col_player].value_counts().head(5)
                for n, v in t.items(): st.markdown(f'**{v}** {n}')
