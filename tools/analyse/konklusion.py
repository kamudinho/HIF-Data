#HIF-Data/tools/analyse/konklusion.py
import streamlit as st
import pandas as pd
from data.utils.team_mapping import (
    TEAMS,
    COMPETITIONS,
    SEASONS,
    SEASON_LEAGUE_MAPPER,
    COMPETITION_NAME,
    TOURNAMENTCALENDAR_NAME as SAESON_NAVN,
)
from data.data_load import _get_snowflake_conn
from data.sql.konklusion_query import hent_konklusion_data

# Metric-definitioner brugt i "Alle hold"-leaderboardet.
METRIC_DEFS = [
    ("Mål scoret", "GOALS", False, 0, "", "Afslutningsspil"),
    ("Expected Goals (xG)", "XG", False, 1, "", "Afslutningsspil"),
    ("Skud i alt", "SHOTS_TOTAL", False, 0, "", "Afslutningsspil"),
    ("Skudpræcision", "SHOT_ACCURACY", False, 1, "%", "Afslutningsspil"),
    ("Skud på mål", "SHOTS_ON_TARGET", False, 0, "", "Afslutningsspil"),
    ("Assists", "ASSISTS", False, 0, "", "Afslutningsspil"),
    ("Expected Assists (xA)", "XA", False, 2, "", "Afslutningsspil"),
    ("Store chancer skabt", "BIG_CHANCES_CREATED", False, 0, "", "Afslutningsspil"),
    ("Store chancer misset", "BIG_CHANCES_MISSED", True, 0, "", "Afslutningsspil"),
    ("Ramt stolpe/overligger", "WOODWORK", False, 0, "", "Afslutningsspil"),

    ("Boldbesiddelse", "POSS", False, 1, "%", "Opbygningsspil"),
    ("Berøringer i alt", "TOUCHES", False, 0, "", "Opbygningsspil"),
    ("Afleveringspræcision", "PASS_ACCURACY", False, 1, "%", "Opbygningsspil"),
    ("Afleveringer i alt", "PASSES_TOTAL", False, 0, "", "Opbygningsspil"),
    ("Berøringer i modst. felt", "BOX_TOUCHES", False, 0, "", "Opbygningsspil"),

    ("Tackling, succes", "TACKLE_SUCCESS", False, 1, "%", "Defensivt spil"),
    ("Vundne tacklinger", "TACKLES_WON", False, 0, "", "Defensivt spil"),
    ("Clearinger", "CLEARANCES", False, 0, "", "Defensivt spil"),
    ("Offsides fanget", "OFFSIDES_WON", False, 0, "", "Defensivt spil"),
    ("xG imod (lavest = bedst)", "XG_AGAINST", True, 2, "", "Defensivt spil"),
    ("Frispark begået (færrest bedst)", "FOULS_CONCEDED", True, 0, "", "Defensivt spil"),

    ("Redninger", "SAVES", False, 0, "", "Målmand & dødbolde"),
    ("Clean sheets", "CLEAN_SHEETS", False, 0, "", "Målmand & dødbolde"),
    ("Mål imod (færrest bedst)", "GOALS_CONCEDED", True, 0, "", "Målmand & dødbolde"),
    ("Straffe reddet", "PENALTY_SAVES", False, 0, "", "Målmand & dødbolde"),
    ("Hjørnespark taget", "CORNERS_TAKEN", False, 0, "", "Målmand & dødbolde"),

    ("Gule kort (færrest bedst)", "YELLOW_CARDS", True, 0, "", "Disciplin"),
    ("Røde kort (færrest bedst)", "RED_CARDS", True, 0, "", "Disciplin"),
]

def vis_side(dp=None):
    # --- 1. SETUP ---
    LIGA_UUID = SEASONS.get(SAESON_NAVN, {}).get(COMPETITION_NAME)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    if not LIGA_UUID:
        st.warning(f"Ingen turnerings-UUID fundet for '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'. Tjek SEASONS-mappingen i team_mapping.py.")
        return

    # --- 2. HENT DATA VIA SQL MODUL ---
    df = hent_konklusion_data(conn, LIGA_UUID)

    if df.empty:
        st.warning(f"Ingen kampstatistik fundet for turneringen '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'.")
        return

    # Sikre grundlæggende beregnede kolonner, hvis de ikke allerede findes
    if 'SHOT_ACCURACY' not in df.columns:
        df['SHOT_ACCURACY'] = (df['SKUD_PAA_MAAL'] / df['TOTAL_SKUD'].replace(0, pd.NA)) * 100
    if 'PASS_ACCURACY' not in df.columns:
        df['PASS_ACCURACY'] = 0.0  # Kan udbygges hvis pass-accuracy kolonnen tilføjes i SQL
    if 'TACKLE_SUCCESS' not in df.columns:
        df['TACKLE_SUCCESS'] = 0.0

    # Ekskluder 'Liga Gennemsnit' fra enkelt-hold ranglisterne, hvis det er medtaget
    df_teams_only = df[df['TEAM_ID'] != 'LIGA_AVG'].copy()

    # --- 3. UI STYLING ---
    st.markdown("""
        <style>
        .analysis-card { 
            border: 1px solid #e6e6e6; 
            padding: 20px; 
            border-radius: 5px; 
            margin-bottom: 20px; 
            background-color: white;
            min-height: 250px;
        }
        .section-title { font-weight: bold; margin-bottom: 10px; font-size: 1.2rem; border-bottom: 2px solid #C8102E; padding-bottom: 5px; }
        .conclusion-text { color: #C8102E; font-weight: bold; margin-top: 15px; text-transform: uppercase; font-size: 0.85rem; }
        .stat-line { margin-bottom: 8px; font-size: 0.95rem; }
        table { text-align: center !important; }
        th { text-align: center !important; }
        td { text-align: center !important; }
        [data-testid="stDataFrame"] th:nth-child(1), 
        [data-testid="stDataFrame"] td:nth-child(1) {
            min-width: 180px !important;
            max-width: 220px !important;
            white-space: normal !important;
            text-align: left !important;
        }
        [data-testid="stDataFrame"] th:nth-child(1) {
            text-align: left !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. HJÆLPEFUNKTIONER ---
    uuid_to_name = {
        str(info.get('opta_uuid')).strip().upper(): name
        for name, info in TEAMS.items() if info.get('opta_uuid')
    }

    def get_ordinal(n):
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    def get_rank(col, ascending=False):
        temp = df_teams_only.dropna(subset=[col]).sort_values(col, ascending=ascending).reset_index(drop=True)
        try:
            rank = temp[temp['TEAM_ID'] == target_uuid].index[0] + 1
            return get_ordinal(rank)
        except Exception:
            return "**?**"

    def get_leader_and_worst(col, ascending=False):
        if col not in df_teams_only.columns:
            return None, None, None, None
        temp = df_teams_only.dropna(subset=[col])
        if temp.empty:
            return None, None, None, None
        
        temp_best = temp.sort_values(col, ascending=ascending)
        best = temp_best.iloc[0]
        best_name = best.get('TEAM_NAME', uuid_to_name.get(best.get('TEAM_ID'), best.get('TEAM_ID')))
        
        temp_worst = temp.sort_values(col, ascending=not ascending)
        worst = temp_worst.iloc[0]
        worst_name = worst.get('TEAM_NAME', uuid_to_name.get(worst.get('TEAM_ID'), worst.get('TEAM_ID')))
        
        return best_name, best[col], worst_name, worst[col]

    def safe_val(val, decimals=1, suffix=""):
        if pd.isna(val):
            return "N/A"
        return f"{val:.{decimals}f}{suffix}"

    # --- 5. FILTRERING ---
    hold_navne = SEASON_LEAGUE_MAPPER.get(SAESON_NAVN, {}).get(COMPETITION_NAME, [])
    sorterede_hold_navne = sorted([n for n in hold_navne if n in TEAMS])
    hold_options = {n: TEAMS[n].get("opta_uuid") for n in sorterede_hold_navne}

    if not hold_options:
        st.warning(f"Ingen hold fundet for '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'.")
        return

    # --- 5b. TOP LINJE: DROPDOWN OG SEGMENTED CONTROL ---
    col_top1, col_top2 = st.columns([1, 1])

    with col_top1:
        valgt_navn = st.selectbox("Vælg hold", sorterede_hold_navne)

    with col_top2:
        visning = st.segmented_control(
            " ",
            ["Enkelt hold", "Alle hold (bedste og dårligste pr. metric)", "Holdtabel (Y-akse)"],
            default="Enkelt hold",
            selection_mode="single"
        )

    target_uuid = str(hold_options[valgt_navn]).strip().upper()

    if visning == "Alle hold (bedste og dårligste pr. metric)":
        rows = []
        for label, col, ascending, decimals, suffix, kategori in METRIC_DEFS:
            best_team, best_val, worst_team, worst_val = get_leader_and_worst(col, ascending=ascending)
            if best_team is None:
                continue
            rows.append({
                "Kategori": kategori,
                "Metric": label,
                "Bedste hold": best_team,
                "Bedste værdi": safe_val(best_val, decimals, suffix),
                "Dårligste hold": worst_team,
                "Dårligste værdi": safe_val(worst_val, decimals, suffix),
            })

        if not rows:
            st.warning("Ingen data at vise for de valgte metrics.")
            return

        df_leaders = pd.DataFrame(rows)
        for kategori in df_leaders['Kategori'].unique():
            st.markdown(f"**{kategori}**")
            st.dataframe(
                df_leaders[df_leaders['Kategori'] == kategori][['Metric', 'Bedste hold', 'Bedste værdi', 'Dårligste hold', 'Dårligste værdi']],
                hide_index=True,
                use_container_width=True,
            )
        return

    elif visning == "Holdtabel (Y-akse)":
        kategorier = []
        for _, _, _, _, _, cat in METRIC_DEFS:
            if cat not in kategorier:
                kategorier.append(cat)

        raw_team_data = []
        for _, r in df_teams_only.iterrows():
            t_name = r.get('TEAM_NAME', uuid_to_name.get(r['TEAM_ID'], r['TEAM_ID']))
            row_data = {"Hold": t_name, "TEAM_ID": r['TEAM_ID']}
            for label, col, _, _, _, _ in METRIC_DEFS:
                if col in r:
                    row_data[col] = r[col]
                else:
                    row_data[col] = pd.NA
            raw_team_data.append(row_data)

        if not raw_team_data:
            st.warning("Ingen data at vise i tabellen.")
            return

        df_raw_teams = pd.DataFrame(raw_team_data)

        for cat in kategorier:
            st.markdown(f"### {cat}")
            cat_defs = [m for m in METRIC_DEFS if m[5] == cat]
            
            display_rows = []
            for _, r in df_raw_teams.iterrows():
                t_name = r["Hold"]
                row_disp = {"Hold": t_name}
                for label, col, ascending, decimals, suffix, _ in cat_defs:
                    val = r[col]
                    row_disp[label] = safe_val(val, decimals, suffix)
                display_rows.append(row_disp)
            
            df_cat = pd.DataFrame(display_rows).sort_values("Hold").set_index("Hold")
            
            def style_cells(data):
                styled = pd.DataFrame('', index=data.index, columns=data.columns)
                for col_name in data.columns:
                    col_key = next((m[1] for m in cat_defs if m[0] == col_name), None)
                    if not col_key:
                        continue
                    temp_sorted = df_raw_teams.dropna(subset=[col_key]).sort_values(col_key, ascending=next(m[2] for m in cat_defs if m[0] == col_name)).reset_index(drop=True)
                    for idx, row in data.iterrows():
                        orig_row = df_raw_teams[df_raw_teams['Hold'] == idx]
                        if orig_row.empty:
                            continue
                        t_id = orig_row.iloc[0]['TEAM_ID']
                        val = orig_row.iloc[0][col_key]
                        if pd.isna(val):
                            continue
                        try:
                            rank_idx = temp_sorted[temp_sorted['TEAM_ID'] == t_id].index[0] + 1
                            total_n = len(temp_sorted)
                            if rank_idx == 1:
                                styled.loc[idx, col_name] = 'background-color: rgba(40, 167, 69, 0.35); text-align: center;'
                            elif rank_idx == 2:
                                styled.loc[idx, col_name] = 'background-color: rgba(40, 167, 69, 0.22); text-align: center;'
                            elif rank_idx == 3:
                                styled.loc[idx, col_name] = 'background-color: rgba(40, 167, 69, 0.12); text-align: center;'
                            elif rank_idx == total_n:
                                styled.loc[idx, col_name] = 'background-color: rgba(220, 53, 69, 0.35); text-align: center;'
                            elif rank_idx == total_n - 1:
                                styled.loc[idx, col_name] = 'background-color: rgba(220, 53, 69, 0.22); text-align: center;'
                            elif rank_idx == total_n - 2:
                                styled.loc[idx, col_name] = 'background-color: rgba(220, 53, 69, 0.12); text-align: center;'
                            else:
                                styled.loc[idx, col_name] = 'text-align: center;'
                        except Exception:
                            styled.loc[idx, col_name] = 'text-align: center;'
                return styled

            styled_df = df_cat.style.apply(style_cells, axis=None).set_properties(**{'text-align': 'center'})
            st.dataframe(styled_df, use_container_width=True, height=470, hide_index=False)
        return

    # --- 6. ENKELT HOLD-VISNING ---
    row_match = df[df['TEAM_ID'] == target_uuid]
    if row_match.empty:
        st.warning(f"Ingen data fundet for {valgt_navn}.")
        return
    row = row_match.iloc[0]

    goals_val = row.get('SCORINGER_MAAL', 0)
    xg_val = row.get('XG', 0)
    diff = goals_val - xg_val
    if diff > 2.0:
        præstation_tekst = "overpræsterer markant (flere mål end xG)"
    elif diff > 0.5:
        præstation_tekst = "overpræsterer (flere mål end xG)"
    elif diff < -2.0:
        præstation_tekst = "underpræsterer markant (færre mål end xG)"
    elif diff < -0.5:
        præstation_tekst = "underpræsterer (færre mål end xG)"
    else:
        præstation_tekst = "præsterer normalt i forhold til xG"

    col1, col2 = st.columns(2)

    with col2:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Afslutningsspil</div>
            <div class="stat-line">• {get_rank('SCORINGER_MAAL')} flest mål scoret ({int(row.get('GOALS', 0))})</div>
            <div class="stat-line">• {get_rank('XG')} højeste expected goals ({row.get('XG', 0):.1f} xG)</div>
            <div class="stat-line">• Forskel: {row.get('GOALS', 0) - row.get('XG', 0):.1f} mål vs xG</div>
            <div class="stat-line">• {get_rank('TOTAL_SKUD')} flest skud i alt ({int(row.get('TOTAL_SKUD', 0))})</div>
            <div class="stat-line">• Skudpræcision: {safe_val(row.get('SHOT_ACCURACY', 0), suffix='%')}</div>
            <div class="stat-line">• {get_rank('BIG_CHANCES_CREATED')} flest store chancer skabt ({int(row.get('BIG_CHANCES_CREATED', 0))})</div>
            <div class="stat-line">• Ramt stolpe/overligger: {int(row.get('WOODWORK', 0))}</div>
            <div class="conclusion-text">Konklusion – {valgt_navn} {præstation_tekst} med {goals_val:.0f} mål mod {xg_val:.1f} xG.</div>
        </div>
        """, unsafe_allow_html=True)

    with col1:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Opbygningsspil</div>
            <div class="stat-line">• {get_rank('BOLDBESIDDELSE_PCT')} højeste boldbesiddelse ({row.get('BOLDBESIDDELSE_PCT', 0):.1f}%)</div>
            <div class="stat-line">• {get_rank('TOUCHES')} flest berøringer i alt ({int(row.get('TOUCHES', 0))})</div>
            <div class="stat-line">• Afleveringspræcision: {safe_val(row.get('PASS_ACCURACY', 0), suffix='%')}</div>
            <div class="stat-line">• {get_rank('XA', ascending=False)} højeste expected assists ({row.get('XA', 0):.2f} xA)</div>
            <div class="stat-line">• {get_rank('BOX_TOUCHES')} flest berøringer i modstanderens felt ({int(row.get('BOX_TOUCHES', 0))})</div>
            <div class="stat-line">• Gennemsnitlig distance: {safe_val(row.get('GENNEMSNITSLIG_DISTANCE', 0), suffix=' km')}</div>
            <div class="conclusion-text">Konklusion – Opbygningsstatistikker indlæst.</div>
        </div>
        """, unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Forsvarsspil</div>
            <div class="stat-line">• Tacklinger, succes: {safe_val(row.get('TACKLE_SUCCESS', 0), suffix='%')} ({int(row.get('VUNDNE_TAKKLINGER', 0))})</div>
            <div class="stat-line">• {get_rank('CLEARANCES')} flest clearinger ({int(row.get('CLEARANCES', 0))})</div>
            <div class="stat-line">• {get_rank('OFFSIDES_WON')} flest offsides ({int(row.get('OFFSIDES_WON', 0))})</div>
            <div class="stat-line">• {get_rank('PPDA', ascending=True)} laveste PPDA ({safe_val(row.get('PPDA', 0), decimals=2)})</div>
            <div class="stat-line">• {get_rank('XG_AGAINST', ascending=True)} laveste xG imod ({safe_val(row.get('XG_AGAINST', 0), decimals=2)})</div>
            <div class="conclusion-text">Konklusion – Presser med en PPDA på {safe_val(row.get('PPDA', 0), decimals=2)}.</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Målmand & standarder</div>
            <div class="stat-line">• {get_rank('SAVES')} flest redninger ({int(row.get('SAVES', 0))})</div>
            <div class="stat-line">• {get_rank('CLEAN_SHEETS')} flest clean sheets ({int(row.get('CLEAN_SHEETS', 0))})</div>
            <div class="stat-line">• {get_rank('MAAL_IMOD', ascending=True)} færrest mål imod ({int(row.get('MAAL_IMOD', 0))})</div>
            <div class="stat-line">• Hjørnespark taget: {int(row.get('VUNDNE_HJORNESPARK', 0))}</div>
            <div class="conclusion-text">Konklusion – {int(row.get('CLEAN_SHEETS', 0))} clean sheets og {int(row.get('MAAL_IMOD', 0))} mål imod.</div>
        </div>
        """, unsafe_allow_html=True)

    col5, _ = st.columns(2)

    with col5:
        total_kort = int(row.get('YELLOW_CARDS', 0) + row.get('SECOND_YELLOWS', 0) + row.get('RED_CARDS', 0))
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Disciplin</div>
            <div class="stat-line">• {get_rank('YELLOW_CARDS', ascending=True)} færrest gule kort ({int(row.get('YELLOW_CARDS', 0))})</div>
            <div class="stat-line">• Direkte røde kort: {int(row.get('RED_CARDS', 0))}</div>
            <div class="stat-line">• Udvisninger efter 2. gule: {int(row.get('SECOND_YELLOWS', 0))}</div>
            <div class="conclusion-text">Konklusion – {total_kort} kort i alt denne sæson.</div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
