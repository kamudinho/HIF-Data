import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from data.utils.team_mapping import COMPETITION_NAME
from tools.hifanalyse.modstander_common import (
    render_hold_saeson_selector,
    fetch_full_match_history,
    fetch_event_data,
    draw_match_row,
)


def vis_side():
    valgt_saeson, valgt_hold_navn, valgt_uuid, hold_logo, liga_ids_sql = render_hold_saeson_selector()

    with st.spinner(f"Henter kampe for {valgt_hold_navn} ({valgt_saeson})..."):
        df_res = fetch_full_match_history(valgt_uuid, liga_ids_sql, valgt_saeson)

    if df_res is None or df_res.empty:
        st.warning(f"Der er endnu ikke registreret nogen kampe for {valgt_hold_navn} i sæsonen {valgt_saeson}.")
        return

    df_res = df_res.copy()
    df_res['USE_DATE'] = df_res['MATCH_DATE_FULL'].fillna(df_res['MATCH_LOCALDATE'])
    df_res['MATCH_LOCALDATE_DT'] = pd.to_datetime(df_res['USE_DATE'], errors='coerce')
    df_res['MATCH_DATE_ONLY'] = df_res['MATCH_LOCALDATE_DT'].dt.date

    df_res['IS_PLAYED'] = (
        df_res['TOTAL_HOME_SCORE'].notnull() & df_res['TOTAL_AWAY_SCORE'].notnull()
    ) | df_res['MATCH_STATUS'].astype(str).str.contains("Played|Full|Finish", case=False, na=False)

    def calc_res(r):
        if not r['IS_PLAYED'] or pd.isna(r['TOTAL_HOME_SCORE']) or pd.isna(r['TOTAL_AWAY_SCORE']):
            return "-"
        if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE']:
            return "D"
        if (r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or \
           (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE']):
            return "W"
        return "L"

    df_res['RES'] = df_res.apply(calc_res, axis=1)

    df_played = df_res[df_res['IS_PLAYED']].sort_values('MATCH_LOCALDATE_DT', ascending=False)
    df_upcoming = df_res[~df_res['IS_PLAYED']].sort_values('MATCH_LOCALDATE_DT', ascending=True)

    target_total = 10
    n_played_to_take = min(len(df_played), target_total)
    df_played_sel = df_played.head(n_played_to_take)

    remaining_slots = target_total - len(df_played_sel)
    df_upcoming_sel = df_upcoming.head(remaining_slots) if remaining_slots > 0 else pd.DataFrame(columns=df_res.columns)

    if not df_upcoming_sel.empty and not df_played_sel.empty:
        df_res_table = pd.concat([
            df_played_sel.sort_values('MATCH_LOCALDATE_DT', ascending=False),
            df_upcoming_sel.sort_values('MATCH_LOCALDATE_DT', ascending=True)
        ])
    elif not df_upcoming_sel.empty:
        df_res_table = df_upcoming_sel.sort_values('MATCH_LOCALDATE_DT', ascending=True).head(10)
    else:
        df_res_table = df_played_sel.sort_values('MATCH_LOCALDATE_DT', ascending=False).head(10)

    # De sidste (op til) 10 SPILLEDE kampe bruges til event-baserede trend-grafer.
    # NB: udledt direkte af df_played_sel ovenfor, i stedet for en ekstra SQL-forespørgsel
    # (den oprindelige kode kørte to næsten identiske "seneste kampe"-forespørgsler).
    match_ids = tuple(df_played_sel['MATCH_OPTAUUID'].tolist())

    with st.spinner("Henter aktionsdata til trend-grafer..."):
        df_all_h = fetch_event_data(valgt_uuid, match_ids)

    if df_all_h.empty:
        df_vol = pd.DataFrame(columns=['MATCH_OPTAUUID'])
    else:
        df_vol = df_all_h.groupby('MATCH_OPTAUUID').agg(
            P_tot=('EVENT_TYPEID', lambda x: (x == 1).sum()),
            P_suc=('EVENT_TYPEID', lambda x: ((df_all_h.loc[x.index, 'EVENT_TYPEID'] == 1) & (df_all_h.loc[x.index, 'OUTCOME'] == 1)).sum()),
            A_tot=('EVENT_TYPEID', lambda x: x.isin([13, 14, 15, 16]).sum()),
            A_suc=('EVENT_TYPEID', lambda x: (df_all_h.loc[x.index, 'EVENT_TYPEID'] == 16).sum()),
            E_tot=('EVENT_TYPEID', lambda x: x.isin([12, 127, 49]).sum()),
            E_suc=('EVENT_TYPEID', lambda x: ((df_all_h.loc[x.index, 'EVENT_TYPEID'].isin([12, 127, 49])) & (df_all_h.loc[x.index, 'OUTCOME'] == 1)).sum()),
            D_tot=('EVENT_TYPEID', lambda x: x.isin([7, 8]).sum()),
            D_suc=('EVENT_TYPEID', lambda x: ((df_all_h.loc[x.index, 'EVENT_TYPEID'].isin([7, 8])) & (df_all_h.loc[x.index, 'OUTCOME'] == 1)).sum()),
            F_tot=('EVENT_TYPEID', lambda x: (x == 4).sum()),
            F_suc=('EVENT_TYPEID', lambda x: (x == 4).sum())
        ).reset_index()

    df_plot_source = df_played_sel.sort_values('MATCH_LOCALDATE_DT', ascending=True)
    df_plot = df_plot_source.merge(df_vol, on='MATCH_OPTAUUID', how='left').fillna(0)

    if not df_plot.empty:
        df_plot['LABEL'] = pd.to_datetime(df_plot['MATCH_DATE_ONLY']).dt.strftime('%d/%m')
        df_plot = df_plot.sort_values('MATCH_LOCALDATE_DT')
        df_plot['OPP_NAME'] = df_plot.apply(lambda r: r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1)
        name_fix = {"B 9": "B93", "HB": "HBK"}
        df_plot['OPP_NAME_CLEAN'] = df_plot['OPP_NAME'].replace(name_fix)
        df_plot['X_AXIS_LABEL'] = df_plot['LABEL'] + "<br>" + df_plot['OPP_NAME_CLEAN'].str.upper()

    st.markdown("""
        <style>
        [data-testid="stMetric"] { text-align: center; display: flex; flex-direction: column; align-items: center; width: 100%; }
        [data-testid="stMetricLabel"] { display: flex; justify-content: center; align-items: center; width: 100%; font-size: 11px !important; margin-bottom: -10px !important; }
        [data-testid="stMetricValue"] { display: flex; justify-content: center; align-items: center; width: 100%; font-size: 20px !important; font-weight: 700; }
        .metric-row-wrapper { margin-top: -35px; margin-bottom: -25px; }
        .compact-divider { margin-top: -5px; margin-bottom: 5px; border-top: 1px solid #f0f2f6; }
        </style>
        """, unsafe_allow_html=True)

    m_col1, m_spacer, m_col2 = st.columns([1.3, 0.1, 2.0])
    with m_col1:
        st.write(f"**Kampe ({valgt_saeson} - {COMPETITION_NAME})**")
        with st.container(border=True):
            st.markdown('<div class="metric-row-wrapper">', unsafe_allow_html=True)
            wins, draws, losses = (df_played['RES'] == "W").sum(), (df_played['RES'] == "D").sum(), (df_played['RES'] == "L").sum()
            mål_s = sum([row['TOTAL_HOME_SCORE'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['TOTAL_AWAY_SCORE'] for _, row in df_played.iterrows() if pd.notnull(row['TOTAL_HOME_SCORE'])])
            mål_i = sum([row['TOTAL_AWAY_SCORE'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['TOTAL_HOME_SCORE'] for _, row in df_played.iterrows() if pd.notnull(row['TOTAL_HOME_SCORE'])])
            met_cols = st.columns(5)
            met_cols[0].metric("Pts", (wins * 3) + draws)
            met_cols[1].metric("V", wins)
            met_cols[2].metric("U", draws)
            met_cols[3].metric("T", losses)
            met_cols[4].metric("Mål", f"{int(mål_s)}-{int(mål_i)}")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)

            for _, row in df_res_table.iterrows():
                d_val = row['MATCH_DATE_ONLY']
                date_str = d_val.strftime('%d/%m') if pd.notnull(d_val) else "-"

                if row['IS_PLAYED'] and pd.notnull(row['TOTAL_HOME_SCORE']) and pd.notnull(row['TOTAL_AWAY_SCORE']):
                    score_display = f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}"
                    res_val = row['RES']
                else:
                    match_dt = row['MATCH_LOCALDATE_DT']
                    time_str = match_dt.strftime('%H:%M') if pd.notnull(match_dt) else ""
                    score_display = time_str if time_str and time_str != '00:00' else "TBD"
                    res_val = "-"

                draw_match_row(date_str, row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], score_display, row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], res_val)
                st.markdown("<hr style='margin:2px 0; opacity:0.05'>", unsafe_allow_html=True)

    with m_col2:
        kat_map = {"Pasninger": 'P', "Afslutninger": 'A', "Erobringer": 'E', "Dueller": 'D', "Frispark": 'F'}
        col_map = {'P': '#084594', 'A': '#cb181d', 'E': '#238b45', 'D': '#ec7014', 'F': '#6a51a3'}

        if not df_plot.empty:
            h_c1, d_c1 = st.columns([2, 1])
            val1 = d_c1.selectbox("Vælg", list(kat_map.keys()), index=0, key="val_top", label_visibility="collapsed")
            c_key1 = kat_map[val1]
            avg1 = df_plot[f'{c_key1}_tot'].mean()
            h_c1.markdown(f"**{val1} (Gns: {round(avg1, 1)})**")

            fig1 = px.bar(df_plot, x='X_AXIS_LABEL', y=f"{c_key1}_tot", text=f"{c_key1}_tot")
            fig1.add_hline(y=avg1, line_dash="dot", line_color="rgba(0,0,0,0.2)", line_width=1)
            fig1.update_traces(
                marker_color=col_map[c_key1],
                textposition='outside',
                customdata=np.stack((df_plot['OPP_NAME_CLEAN'], df_plot['LABEL'], [val1.lower()] * len(df_plot)), axis=-1),
                hovertemplate="vs. %{customdata[0]}<br>%{customdata[1]}<br><br><b>%{y} %{customdata[2]}</b><extra></extra>"
            )
            fig1.update_layout(height=300, margin=dict(t=25, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)',
                                xaxis_title=None, yaxis_title=None, hoverlabel=dict(bgcolor="white", font_size=12))
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

            options_2 = [k for k in kat_map.keys() if k != val1]
            h_c2, d_c2 = st.columns([2, 1])
            val2 = d_c2.selectbox("Vælg", options_2, index=0, key="val_bot", label_visibility="collapsed")
            c_key2 = kat_map[val2]
            avg2 = df_plot[f'{c_key2}_tot'].mean()
            h_c2.markdown(f"**{val2} (Gns: {round(avg2, 1)})**")

            fig2 = px.bar(df_plot, x='X_AXIS_LABEL', y=f"{c_key2}_tot", text=f"{c_key2}_tot")
            fig2.add_hline(y=avg2, line_dash="dot", line_color="rgba(0,0,0,0.2)", line_width=1)
            fig2.update_traces(
                marker_color=col_map[c_key2],
                textposition='outside',
                customdata=np.stack((df_plot['OPP_NAME_CLEAN'], df_plot['LABEL'], [val2.lower()] * len(df_plot)), axis=-1),
                hovertemplate="vs. %{customdata[0]}<br>%{customdata[1]}<br><br><b>%{y} %{customdata[2]}</b><extra></extra>"
            )
            fig2.update_layout(height=300, margin=dict(t=25, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)',
                                xaxis_title=None, yaxis_title=None, hoverlabel=dict(bgcolor="white", font_size=12))
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Ingen spillede kampe fundet til at generere grafer endnu.")


if __name__ == "__main__":
    vis_side()
