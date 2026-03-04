import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

HIF_RED, HIF_GOLD = '#cc0000', '#b8860b'

def vis_side(dp):
    df_hif = dp.get('playerstats', pd.DataFrame())
    if df_hif.empty:
        st.error("Ingen data fundet.")
        return

    # Sørg for numeriske typer
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_X', 'PASS_Y', 'XG_VAL', 'IS_ASSIST']:
        df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "CHANCESKABELSE"])

    with tab1:
        df_skud = df_hif[df_hif['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        v_skud = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_skud['PLAYER_NAME'].unique().tolist()))
        df_vis = df_skud if v_skud == "Hele Holdet" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
        
        pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white')
        fig, ax = pitch.draw()
        pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=df_vis['XG_VAL']*800+50, c=HIF_RED, ax=ax)
        st.pyplot(fig)

    with tab2:
        # VIS KUN REELLE CHANCER (IS_ASSIST er 1)
        df_a = df_hif[df_hif['IS_ASSIST'] == 1].copy()
        v_a = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_a['PLAYER_NAME'].unique().tolist()), key="as")
        df_a_vis = df_a if v_a == "Hele Holdet" else df_a[df_a['PLAYER_NAME'] == v_a]

        pitch_a = VerticalPitch(half=True, pitch_type='opta')
        fig_a, ax_a = pitch_a.draw()
        for _, r in df_a_vis.iterrows():
            pitch_a.arrows(r['PASS_X'], r['PASS_Y'], r['EVENT_X'], r['EVENT_Y'], color=HIF_GOLD, ax=ax_a)
        st.pyplot(fig_a)
