# tools/hifanalyse/modstander_heatmaps.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from data.utils.team_mapping import COMPETITION_NAME
from tools.hifanalyse.modstander_common import (
    render_hold_saeson_selector,
    fetch_full_match_history,
    fetch_event_data,
    fetch_zone_aggregates,
    draw_match_row,
    plot_custom_pitch,
)

def vis_side():
    # 1. Hent valg fra brugeren via common.py
    valgt_saeson, valgt_hold_navn, valgt_uuid, hold_logo, liga_ids_sql = render_hold_saeson_selector()

    with st.spinner(f"Henter data for {valgt_hold_navn} ({valgt_saeson})..."):
        df_res = fetch_full_match_history(valgt_uuid, liga_ids_sql, valgt_saeson)

    if df_res is None or df_res.empty:
        st.warning(f"Der er endnu ikke spillet/registreret nogen færdigspillede kampe for {valgt_hold_navn} i sæsonen {valgt_saeson}.")
        return

    # 2. Hent event-data (aktioner) baseret på kamp-ID'er
    match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
    df_all_h = fetch_event_data(valgt_uuid, match_ids)

    if df_all_h.empty:
        st.info("Ingen aktionsdata fundet for de seneste kampe.")
        return

    n_matches = df_all_h['MATCH_OPTAUUID'].nunique()
    total_minutes = n_matches * 90

    # 3. Opret Tabs
    t2, t3 = st.tabs(["MED BOLDEN", "UDEN BOLDEN"])

    # ---------------------------------------------------------------------------
    # TAB 2: MED BOLDEN
    # ---------------------------------------------------------------------------
    with t2:
        st.markdown("""
                   <style>
                   [data-testid="stHorizontalBlock"] [data-testid="stMetric"] { text-align: center; align-items: center; justify-content: center; width: 100%; }
                   [data-testid="stMetricLabel"] { justify-content: center !important; font-size: 10px !important; white-space: nowrap; margin-bottom: -3px !important; }
                   [data-testid="stMetricValue"] { justify-content: center !important; font-size: 14px !important; font-weight: 700; }
                   </style>
                   """, unsafe_allow_html=True)

        kat_options = ["Fase 1", "Gennembrud", "Touches in Box", "Afslutninger"]
        c_left, c_right = st.columns([2, 1])
        v_med = c_right.selectbox("Vælg Fokusområde", kat_options, key="ms_t2", label_visibility="collapsed")

        # Logik til filtrering baseret på valg
        if v_med == "Fase 1":
            ids, tit, cm, zn = [1], "OPBYGNING", "Reds", "up"
            df_f = df_all_h[(df_all_h['EVENT_Y'] <= 50) & (df_all_h['EVENT_TYPEID'] == 1)].copy()
        
        elif v_med == "Gennembrud":
            ids, tit, cm, zn = [1], "GENNEMBRUD", "Blues", "down"
            df_f = df_all_h[(df_all_h['EVENT_Y'] > 50) & (df_all_h['EVENT_TYPEID'] == 1)].copy()
        
        elif v_med == "Touches in Box":
            ids, tit, cm, zn = [0], "TOUCHES IN BOX", "Blues", "down"
            # Begræns til boks-området (Y > 83 og X mellem 15-85)
            df_f = df_all_h[(df_all_h['EVENT_Y'] > 83) & (df_all_h['EVENT_X'] > 15) & (df_all_h['EVENT_X'] < 85)].copy()
            df_shots = df_all_h[df_all_h['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()

        else: # Afslutninger
            ids, tit, cm, zn = [13, 14, 15, 16], "AFSLUTNINGER", "YlOrRd", "down"
            df_f = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].copy()

        total_act = len(df_f)

        # Vis Heatmap
        with c_left:
            # Hvis "Touches in Box", bruger vi alle event_type_ids i det filtrerede df
            plot_ids = df_f['EVENT_TYPEID'].unique().tolist() if v_med == "Touches in Box" else ids
            st.pyplot(plot_custom_pitch(df_f, plot_ids, tit, zone=zn, cmap=cm, logo=hold_logo))

        # Vis Metrics og Top 8
        with c_right:
            if v_med == "Touches in Box":
                shots_total = len(df_shots)
                touches_p90 = (total_act / total_minutes * 90) if total_minutes > 0 else 0
                conv_box = (shots_total / total_act * 100) if total_act > 0 else 0
                m_cols = st.columns(3)
                m_cols[0].metric("Touches", total_act)
                m_cols[1].metric("p90", round(touches_p90, 1))
                m_cols[2].metric("Afsl/Box %", f"{int(conv_box)}%")
            
            elif v_med == "Afslutninger":
                goals = len(df_f[df_f['EVENT_TYPEID'] == 16])
                shots_p90 = (total_act / total_minutes * 90) if total_minutes > 0 else 0
                goals_p90 = (goals / total_minutes * 90) if total_minutes > 0 else 0
                conv_rate = (goals / total_act * 100) if total_act > 0 else 0
                m_cols = st.columns(5)
                m_cols[0].metric("Skud", total_act)
                m_cols[1].metric("p90", round(shots_p90, 1))
                m_cols[2].metric("Mål", goals)
                m_cols[3].metric("p90", round(goals_p90, 1))
                m_cols[4].metric("Konv %", f"{int(conv_rate)}%")
            
            else: # Fase 1 og Gennembrud
                acc_pct = (df_f['OUTCOME'].sum() / total_act * 100) if total_act > 0 else 0
                avg_p90 = (total_act / total_minutes * 90) if total_minutes > 0 else 0
                m_cols = st.columns(3)
                m_cols[0].metric("Total", total_act)
                m_cols[1].metric("Gns p90", round(avg_p90, 1))
                m_cols[2].metric("Succes", f"{int(acc_pct)}%")

            st.markdown("<div style='margin-top:10px; border-top: 1px solid #eee; padding-top: 10px;'></div>", unsafe_allow_html=True)
            st.write(f"**Top 8: {v_med}**")

            if not df_f.empty:
                df_top = df_f.groupby('PLAYER_NAME').agg(TOTAL=('EVENT_TYPEID', 'count'), SUCCESS=('OUTCOME', 'sum')).reset_index()
                
                if v_med == "Afslutninger":
                    # Sikr at succes kun tæller mål (16) i top-listen for afslutninger
                    df_top['SUCCESS'] = df_f[df_f['EVENT_TYPEID'] == 16].groupby('PLAYER_NAME').size().reindex(df_top['PLAYER_NAME'], fill_value=0).values

                df_top['RATE'] = (df_top['SUCCESS'] / df_top['TOTAL'] * 100).fillna(0)

                # Filter for at undgå spillere med meget få aktioner
                min_limit = 100 if v_med in ["Fase 1", "Gennembrud"] else 1
                df_top = df_top[df_top['TOTAL'] >= min_limit]
                df_top = df_top.sort_values(['RATE', 'TOTAL'], ascending=[False, False]).head(8)

                if df_top.empty:
                    st.info(f"Ingen spillere med +{min_limit} aktioner")
                else:
                    for _, r in df_top.iterrows():
                        rate_val = int(r['RATE'])
                        st.markdown(f"""
                                   <div style="margin-bottom: 12px;">
                                       <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; margin-bottom: 2px;">
                                           <span>{r['PLAYER_NAME']}</span>
                                           <span>{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({rate_val}%)</span>
                                       </div>
                                       <div style="background-color: #f0f2f6; border-radius: 4px; height: 5px; width: 100%;">
                                           <div style="background-color: #084594; height: 5px; width: {rate_val}%; border-radius: 4px;"></div>
                                       </div>
                                   </div>
                               """, unsafe_allow_html=True)
            else:
                st.info("Ingen data fundet.")

    # ---------------------------------------------------------------------------
    # TAB 3: UDEN BOLDEN
    # ---------------------------------------------------------------------------
    with t3:
        uden_options = ["Egen halvdel: Erobringer", "Off. halvdel: Pres", "Egen halvdel: Dueller", "Off. halvdel: Dueller"]
        c_left, c_right = st.columns([2, 1])
        v_uden = c_right.selectbox("Vælg Fokusområde", uden_options, key="ms_t3", label_visibility="collapsed")

        erobring_ids = [7, 8, 12, 127]
        duel_ids = [7, 44]

        if "Erobringer" in v_uden:
            ids, tit, cm, zn = erobring_ids, "Egen halvdel: EROBRINGER", "Oranges", "up"
            df_f = df_all_h[(df_all_h['EVENT_Y'] <= 50) & (df_all_h['EVENT_TYPEID'].isin(ids))].copy()
        elif "Pres" in v_uden:
            ids, tit, cm, zn = erobring_ids, "Off. halvdel: PRES", "Oranges", "down"
            df_f = df_all_h[(df_all_h['EVENT_Y'] > 50) & (df_all_h['EVENT_TYPEID'].isin(ids))].copy()
        elif "Egen halvdel: Dueller" in v_uden:
            ids, tit, cm, zn = duel_ids, "Egen halvdel: DUELLER", "Oranges", "up"
            df_f = df_all_h[(df_all_h['EVENT_Y'] <= 50) & (df_all_h['EVENT_TYPEID'].isin(ids))].copy()
        else: # Off. halvdel: Dueller
            ids, tit, cm, zn = duel_ids, "Off. halvdel: DUELLER", "Oranges", "down"
            df_f = df_all_h[(df_all_h['EVENT_Y'] > 50) & (df_all_h['EVENT_TYPEID'].isin(ids))].copy()

        total_act = len(df_f)

        with c_left:
            fig = plot_custom_pitch(df_f, ids, tit, zone=zn, cmap=cm, logo=hold_logo)
            st.pyplot(fig)

        with c_right:
            acc_pct = (df_f['OUTCOME'].sum() / total_act * 100) if total_act > 0 else 0
            avg_p90 = (total_act / total_minutes * 90) if total_minutes > 0 else 0

            m_cols = st.columns(3)
            m_cols[0].metric("Total", total_act)
            m_cols[1].metric("p90", round(avg_p90, 1))
            m_cols[2].metric("Succes", f"{int(acc_pct)}%")

            st.markdown("<div style='margin-top:10px; border-top: 1px solid #eee; padding-top: 10px;'></div>", unsafe_allow_html=True)
            st.write(f"**Top 8: {v_uden}**")

            if not df_f.empty:
                df_top = df_f.groupby('PLAYER_NAME').agg(
                    TOTAL=('EVENT_TYPEID', 'count'),
                    SUCCESS=('OUTCOME', 'sum')
                ).reset_index()
                df_top['RATE'] = (df_top['SUCCESS'] / df_top['TOTAL'] * 100).fillna(0)

                df_top = df_top[df_top['TOTAL'] >= 1]
                df_top = df_top.sort_values(['RATE', 'TOTAL'], ascending=[False, False]).head(8)

                for _, r in df_top.iterrows():
                    rate_val = int(r['RATE'])
                    st.markdown(f"""
                        <div style="margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; margin-bottom: 2px;">
                                <span>{r['PLAYER_NAME']}</span>
                                <span>{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({rate_val}%)</span>
                            </div>
                            <div style="background-color: #f0f2f6; border-radius: 4px; height: 5px; width: 100%;">
                                <div style="background-color: #ec7014; height: 5px; width: {rate_val}%; border-radius: 4px;"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Ingen data fundet for dette område.")

if __name__ == "__main__":
    vis_side()
