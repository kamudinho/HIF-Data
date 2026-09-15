import streamlit as st
import pandas as pd
from mplsoccer import Pitch

from modstander_common import (
    render_hold_saeson_selector,
    fetch_goal_sequences,
    get_logo_img,
    draw_match_info_box,
    get_action_label,
)


def vis_side():
    valgt_saeson, valgt_hold_navn, valgt_uuid, hold_logo, liga_ids_sql = render_hold_saeson_selector()

    with st.spinner(f"Henter målsekvenser for {valgt_hold_navn} ({valgt_saeson})..."):
        df_all_events = fetch_goal_sequences(valgt_uuid, liga_ids_sql)

    t4, t5 = st.tabs(["MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t4:
        if not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values(
                ['MATCH_LOCALDATE', 'EVENT_TIMESTAMP'], ascending=[False, False]
            )

            opts = {}
            for i, (_, r) in enumerate(gl.iterrows()):
                key = f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}_{i}"

                dato_str = pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')
                opp_navn = r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['CONTESTANTHOME_NAME']

                kamp_res = f"{int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])}"

                mål_hjemme = int(r['HOME_SCORE']) if 'HOME_SCORE' in r and pd.notna(r['HOME_SCORE']) else int(r['TOTAL_HOME_SCORE'])
                mål_ude = int(r['AWAY_SCORE']) if 'AWAY_SCORE' in r and pd.notna(r['AWAY_SCORE']) else int(r['TOTAL_AWAY_SCORE'])
                mål_stilling = f"{mål_hjemme}-{mål_ude}"

                raw_min = r['GOAL_MIN']
                minuttal = 1 if pd.isna(raw_min) else int(raw_min) + 1

                label_tekst = f"{dato_str}: {mål_stilling} ({minuttal}. min) vs. {opp_navn} ({kamp_res})"

                opts[key] = {
                    'label': label_tekst,
                    'match_id': r['MATCH_OPTAUUID'],
                    'goal_ts': r['GOAL_TIME'],
                    'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['CONTESTANTHOME_OPTAUUID'],
                    'min': minuttal,
                    'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y'),
                    'score_str': kamp_res
                }

            sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x]['label'])
            sd = opts[sk]

            tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sd['match_id']) &
                                 (df_all_events['GOAL_TIME'] == sd['goal_ts'])].sort_values('EVENT_TIMESTAMP').copy()

            p_c, l_c = st.columns([2.5, 1])
            p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
            f, ax = p.draw(figsize=(10, 7))

            draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp_uuid']), sd['date'], sd['score_str'], sd['min'])

            for i in range(len(tge) - 1):
                p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'],
                          tge.iloc[i + 1]['EVENT_X'], tge.iloc[i + 1]['EVENT_Y'],
                          width=1, color='black', alpha=0.15, ax=ax)

            for _, r in tge.iterrows():
                is_goal = str(r['EVENT_TYPEID']) == "16"
                ax.scatter(r['EVENT_X'], r['EVENT_Y'], color='red' if is_goal else 'black', s=100, edgecolors='white', zorder=10)
                ax.text(r['EVENT_X'], r['EVENT_Y'] + 2.5, r['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1), zorder=11)

            p_c.pyplot(f)

            def get_final_label_t4(row):
                if str(row['EVENT_TYPEID']) == "16" and "9" in row['qual_list']:
                    return "STRAFFESPARK"

                if 'Action_Label' in row and pd.notna(row['Action_Label']) and row['Action_Label'] != "":
                    return row['Action_Label']

                label = get_action_label(row)
                return label if label else "Opbygning"

            tge['Aktion'] = tge.apply(get_final_label_t4, axis=1)

            l_c.write("**Målsekvens:**")
            l_c.dataframe(
                tge[['PLAYER_NAME', 'Aktion']].iloc[::-1].rename(columns={'PLAYER_NAME': 'Spiller'}),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info(f"Ingen mål fundet for {valgt_hold_navn} i sæsonen {valgt_saeson}.")

    with t5:
        if not df_all_events.empty:
            df_mål_stats = df_all_events.copy()

            df_mål_stats['is_cross'] = df_mål_stats['qual_list'].apply(lambda x: '2' in x)
            df_mål_stats['is_shot_assist'] = df_mål_stats['qual_list'].apply(lambda x: '210' in x or '209' in x)
            df_mål_stats['is_shot'] = df_mål_stats['EVENT_TYPEID'].isin([13, 14, 15])
            df_mål_stats['is_goal'] = df_mål_stats['EVENT_TYPEID'] == 16

            total_goals_count = df_mål_stats['GOAL_TIME'].nunique()

            player_stats = df_mål_stats.groupby('PLAYER_NAME').agg(
                Involveringer=('GOAL_TIME', 'nunique'),
                Aktioner=('EVENT_TYPEID', 'count'),
                Mål=('is_goal', 'sum'),
                Pasninger=('EVENT_TYPEID', lambda x: (x == 1).sum()),
                Indlæg=('is_cross', 'sum'),
                Skud=('is_shot', 'sum'),
                Skud_Ass=('is_shot_assist', 'sum'),
                Erobringer=('EVENT_TYPEID', lambda x: x.isin([7, 8, 12, 127, 49]).sum())
            ).reset_index()

            player_stats['Involvering_Pct'] = (player_stats['Involveringer'] / total_goals_count * 100).round(1)
            player_stats = player_stats.sort_values('Involveringer', ascending=False)

            col_tabel, col_graf = st.columns([3.5, 1])

            with col_tabel:
                st.write("**Statistik i målsekvenser**")

                df_display = player_stats.rename(columns={
                    'PLAYER_NAME': 'Spiller',
                    'Skud_Ass': 'Skud Ass.'
                })[['Spiller', 'Involveringer', 'Aktioner', 'Mål', 'Pasninger', 'Indlæg', 'Skud', 'Skud Ass.', 'Erobringer']]

                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Spiller": st.column_config.Column(width="medium", alignment="left"),
                        "Involveringer": st.column_config.NumberColumn(width="small", alignment="center", format="%d"),
                        "Aktioner": st.column_config.NumberColumn(width="small", alignment="center", format="%d"),
                        "Mål": st.column_config.NumberColumn(width="small", alignment="center", format="%d"),
                        "Pasninger": st.column_config.NumberColumn(width="small", alignment="center", format="%d"),
                        "Indlæg": st.column_config.NumberColumn(width="small", alignment="center", format="%d"),
                        "Skud": st.column_config.NumberColumn(width="small", alignment="center", format="%d"),
                        "Skud Ass.": st.column_config.NumberColumn(width="small", alignment="center", format="%d"),
                        "Erobringer": st.column_config.NumberColumn(width="small", alignment="center", format="%d"),
                    }
                )

            with col_graf:
                st.write(f"**Målinvolveringer (Samlet mål: {total_goals_count})**")

                for _, r in player_stats.head(12).iterrows():
                    rel_width = r['Involvering_Pct']

                    st.markdown(f"""
                        <div style="margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; margin-bottom: 2px;">
                                <span>{r['PLAYER_NAME']}</span>
                                <span>{int(r['Involveringer'])} målinvolveringer ({int(r['Involvering_Pct'])}%)</span>
                            </div>
                            <div style="background-color: #f0f2f6; border-radius: 4px; height: 5px; width: 100%;">
                                <div style="background-color: #df003b; height: 5px; width: {rel_width}%; border-radius: 4px;"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"Ingen målsekvenser tilgængelige for {valgt_hold_navn} i sæsonen {valgt_saeson}.")


if __name__ == "__main__":
    vis_side()
