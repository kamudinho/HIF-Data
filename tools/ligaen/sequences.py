import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# --- DATA OG MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
from data.utils.mapping import get_action_label
from data.sql.liga_spillere import hent_match_og_haendelsesdata

def vis_side():
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_IDS = "('2mb332vncy4450vu14paj8844', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

    st.title("⚽ Målsekvenser")
    st.markdown("Her kan du gennemgå holdets målsekvenser rent og visuelt.")

    conn = _get_snowflake_conn()
    if not conn:
        st.warning("Kunne ikke oprette forbindelse til databasen.")
        st.stop()

    # 1. Hent holddata og vælg hold
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    if df_teams_raw is not None:
        df_teams_raw.columns = df_teams_raw.columns.str.lower()

    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}

    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['contestanthome_optauuid']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['contestanthome_optauuid']

    team_names = sorted(list(team_map.keys()))
    default_team_idx = next((i for i, name in enumerate(team_names) if "hvidovre" in name.lower()), 0)

    valgt_hold = st.selectbox("Vælg hold", team_names, index=default_team_idx)
    valgt_uuid_hold = team_map[valgt_hold]

    # 2. Hent hændelsesdata
    with st.spinner("Henter målsekvenser..."):
        df_all, df_expected, df_db_stats = hent_match_og_haendelsesdata(
            conn, DB, valgt_uuid_hold, LIGA_IDS, {}
        )

    if df_all is None or df_all.empty:
        st.warning("Ingen hændelsesdata fundet.")
        st.stop()

    # Rens for dubletter
    df_all = df_all.dropna(subset=['visningsnavn'])
    subset_cols = [c for c in ['event_typeid', 'event_x', 'event_y', 'minute', 'second', 'player_optauuid', 'match_id'] if c in df_all.columns]
    if subset_cols:
        df_all = df_all.drop_duplicates(subset=subset_cols)

    df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    # 3. Filtrer kun mål (event_typeid == 16)
    if 'event_typeid' in df_all.columns:
        maal_df = df_all[df_all['event_typeid'] == 16].copy()
    else:
        maal_df = pd.DataFrame()

    if maal_df.empty:
        st.info("Ingen mål fundet i det aktuelle datasæt.")
    else:
        kamp_kolonne = 'match_teams' if 'match_teams' in maal_df.columns else 'match_id'
        maal_df['maal_label'] = (
            "Kamp: " + maal_df[kamp_kolonne].astype(str) + 
            " | Minut: " + maal_df['minute'].astype(str) + "'" +
            " | Målscorer: " + maal_df['visningsnavn'].astype(str)
        )

        col_sel, col_info = st.columns([2, 1])
        with col_sel:
            valgt_maal_label = st.selectbox("Vælg målsekvens", maal_df['maal_label'].unique())

        if valgt_maal_label:
            aktuelt_maal = maal_df[maal_df['maal_label'] == valgt_maal_label].iloc[0]
            kamp_id = aktuelt_maal.get('match_id')
            maal_minut = aktuelt_maal['minute']
            maal_periode = aktuelt_maal.get('period_id', 1)

            # Hent sekvensen op til målet (fx 2 minutter før)
            sekvens_df = df_all[
                (df_all['match_id'] == kamp_id) & 
                (df_all.get('period_id', 1) == maal_periode) & 
                (df_all['minute'] <= maal_minut) & 
                (df_all['minute'] >= maal_minut - 2)
            ].copy()

            sekvens_cols = [c for c in ['event_typeid', 'event_x', 'event_y', 'minute', 'second'] if c in sekvens_df.columns]
            if sekvens_cols:
                sekvens_df = sekvens_df.drop_duplicates(subset=sekvens_cols)
            
            if 'second' in sekvens_df.columns:
                sekvens_df = sekvens_df.sort_values(by=['minute', 'second'])

            with col_info:
                st.metric("Målscorer", str(aktuelt_maal['visningsnavn']))
                st.metric("Tidspunkt", f"{int(maal_minut)}' minut")

            # 4. Tegn banen præcis som på billedet
            st.markdown("### Sekvensopbygning på banen")
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#7f7f7f', line_zorder=2)
            fig, ax = pitch.draw(figsize=(11, 7))

            if not sekvens_df.empty and 'event_x' in sekvens_df.columns:
                sekvens_df = sekvens_df.dropna(subset=['event_x', 'event_y'])
                
                # Tegn grå/lyse opbygningspile mellem hændelserne
                if len(sekvens_df) > 1:
                    pitch.arrows(
                        sekvens_df['event_x'].iloc[:-1], 
                        sekvens_df['event_y'].iloc[:-1],
                        sekvens_df['event_x'].iloc[1:], 
                        sekvens_df['event_y'].iloc[1:], 
                        ax=ax, width=1.5, headwidth=3, color="#cccccc", alpha=0.8, zorder=3
                    )

                # Tegn sorte prikker for opbygningsaktioner
                pitch.scatter(
                    sekvens_df['event_x'], sekvens_df['event_y'],
                    color='black', s=80, ax=ax, zorder=4
                )

                # Tilføj spillernavne over punkterne
                for _, row in sekvens_df.iterrows():
                    if pd.notna(row.get('visningsnavn')) and pd.notna(row.get('event_x')):
                        ax.text(
                            row['event_x'], row['event_y'] + 3, row['visningsnavn'],
                            fontsize=9, ha='center', va='bottom', color='black', zorder=5
                        )

                # Marker selve målet med en rød prik til sidst, så den ligger øverst
                if 'event_typeid' in aktuelt_maal and aktuelt_maal['event_typeid'] == 16:
                    pitch.scatter(
                        aktuelt_maal['event_x'], aktuelt_maal['event_y'],
                        color='#df003b', s=120, ax=ax, zorder=6
                    )
                    ax.text(
                        aktuelt_maal['event_x'], aktuelt_maal['event_y'] + 3, aktuelt_maal['visningsnavn'],
                        fontsize=9, fontweight='bold', ha='center', va='bottom', color='black', zorder=7
                    )

            st.pyplot(fig, use_container_width=True)

            # 5. Vis tabel over sekvensen
            st.markdown("### Aktioner i sekvensen")
            vis_cols = [c for c in ['minute', 'second', 'visningsnavn', 'Action_Label', 'outcome'] if c in sekvens_df.columns]
            if vis_cols:
                st.dataframe(sekvens_df[vis_cols], use_container_width=True, hide_index=True)
