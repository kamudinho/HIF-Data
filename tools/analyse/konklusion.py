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
from data.sql.teams import hent_hoved_stats, hent_samlet_hold_statistik

# Metric-definitioner brugt i "Alle hold"-leaderboardet.
METRIC_DEFS = [
    ("Mål scoret", "GOALS", False, 0, "", "Afslutningsspil"),
    ("Expected Goals (xG)", "XG", False, 1, "", "Afslutningsspil"),
    ("Skud i alt", "SHOTS_TOTAL", False, 0, "", "Afslutningsspil"),
    ("Skudpræcision", "SHOT_ACCURACY", False, 1, "%", "Afslutningsspil"),
    ("Assists", "ASSISTS", False, 0, "", "Afslutningsspil"),
    ("Expected Assists (xA)", "XA", False, 2, "", "Afslutningsspil"),
    ("Store chancer skabt", "BIG_CHANCES_CREATED", False, 0, "", "Afslutningsspil"),
    ("Store chancer misset", "BIG_CHANCES_MISSED", True, 0, "", "Afslutningsspil"),
    ("Ramt stolpe/overligger", "WOODWORK", False, 0, "", "Afslutningsspil"),

    ("Boldbesiddelse", "POSS", False, 1, "%", "Opbygningsspil"),
    ("Berøringer i alt", "TOUCHES", False, 0, "", "Opbygningsspil"),
    ("Afleveringspræcision", "PASS_ACCURACY", False, 1, "%", "Opbygningsspil"),
    ("Berøringer i modst. felt", "BOX_TOUCHES", False, 0, "", "Opbygningsspil"),

    ("Tackling, succes", "TACKLE_SUCCESS", False, 1, "%", "Defensivt spil"),
    ("Clearinger", "CLEARANCES", False, 0, "", "Defensivt spil"),
    ("Offsides fanget", "OFFSIDES_WON", False, 0, "", "Defensivt spil"),
    ("PPDA (lavest = mest pres)", "PPDA", True, 2, "", "Defensivt spil"),
    ("xG imod (lavest = bedst)", "XG_AGAINST", True, 2, "", "Defensivt spil"),
    ("Frispark begået (færrest bedst)", "FOULS_CONCEDED", True, 0, "", "Defensivt spil"),

    ("Redninger", "SAVES", False, 0, "", "Målmand & dødbolde"),
    ("Clean sheets", "CLEAN_SHEETS", False, 0, "", "Målmand & dødbolde"),
    ("Mål imod (færrest bedst)", "GOALS_CONCEDED", True, 0, "", "Målmand & dødbolde"),
    ("Straffe reddet", "PENALTY_SAVES", False, 0, "", "Målmand & dødbolde"),
    ("Hjørnespark taget", "CORNERS_TAKEN", False, 0, "", "Målmand & dødbolde"),
    ("Hjørnespark imod (færrest bedst)", "CORNERS_CONCEDED", True, 0, "", "Målmand & dødbolde"),

    ("Gule kort (færrest bedst)", "YELLOW_CARDS", True, 0, "", "Disciplin"),
    ("Røde kort (færrest bedst)", "RED_CARDS", True, 0, "", "Disciplin"),
]

def vis_side(dp=None):
    # --- 1. SETUP ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = SEASONS.get(SAESON_NAVN, {}).get(COMPETITION_NAME)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    if not LIGA_UUID:
        st.warning(f"Ingen turnerings-UUID fundet for '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'.")
        return

    # --- 2. HENT DATA VIA TEAM SQL MODULER ---
    df_hold = hent_samlet_hold_statistik(conn, LIGA_UUID)
    if df_hold is None or df_hold.empty:
        st.warning(f"Ingen samlet holdstatistik fundet for turneringen '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'.")
        return

    df = df_hold.copy()
    df.columns = [str(c).upper() for c in df.columns]

    # Map kolonnenavne fra hent_samlet_hold_statistik til de nøgler konklusion.py forventer
    column_mapping = {
        'TOTAL_GOALS': 'GOALS',
        'TOTAL_XG': 'XG',
        'XGC_P90': 'XG_AGAINST',
        'AVG_POSSESSION_PCT': 'POSS',
        'TOTAL_SHOTS': 'SHOTS_TOTAL',
        'ON_TARGET_SHOTS': 'SHOTS_ON_TARGET',
        'SHOTS_OFF_TARGET': 'SHOTS_OFF_TARGET',
        'BLOCKED_SHOTS': 'SHOTS_BLOCKED',
        'CORNERS': 'CORNERS_TAKEN',
    }
    df = df.rename(columns=column_mapping)

    # Sikr at TEAM_ID / TEAM_NAME findes og knyttes til TEAMS-mappingen
    name_to_uuid = {name.strip().upper(): str(info.get('opta_uuid')).strip().upper() for name, info in TEAMS.items() if info.get('opta_uuid')}
    if 'TEAM_ID' not in df.columns and 'TEAM_NAME' in df.columns:
        df['TEAM_ID'] = df['TEAM_NAME'].str.strip().str.upper().map(name_to_uuid)

    # Fyld manglende metriske kolonner ud med 0 for at undgå KeyError
    for metric_def in METRIC_DEFS:
        col_key = metric_def[1]
        if col_key not in df.columns:
            df[col_key] = 0.0
        else:
            df[col_key] = pd.to_numeric(df[col_key], errors='coerce').fillna(0.0)

    # Sikre grundlæggende afledte værdier
    if 'SHOTS_ON_TARGET' in df.columns and 'SHOTS_TOTAL' in df.columns:
        df['SHOT_ACCURACY'] = (df['SHOTS_ON_TARGET'] / df['SHOTS_TOTAL'].replace(0, pd.NA)) * 100
    else:
        df['SHOT_ACCURACY'] = 0.0

    df['PASS_ACCURACY'] = 0.0
    df['TACKLE_SUCCESS'] = 0.0

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
        temp = df.dropna(subset=[col]).sort_values(col, ascending=ascending).reset_index(drop=True)
        try:
            rank = temp[temp['TEAM_ID'] == target_uuid].index[0] + 1
            return get_ordinal(rank)
        except Exception:
            return "**?**"

    def get_leader_and_worst(col, ascending=False):
        if col not in df.columns:
            return None, None, None, None
        temp = df.dropna(subset=[col])
        if temp.empty:
            return None, None, None, None
        
        temp_best = temp.sort_values(col, ascending=ascending)
        best = temp_best.iloc[0]
        best_name = uuid_to_name.get(best.get('TEAM_ID'), best.get('TEAM_NAME', 'Ukendt'))
        
        temp_worst = temp.sort_values(col, ascending=not ascending)
        worst = temp_worst.iloc[0]
        worst_name = uuid_to_name.get(worst.get('TEAM_ID'), worst.get('TEAM_NAME', 'Ukendt'))
        
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
        for _, r in df.iterrows():
            t_name = uuid_to_name.get(r.get('TEAM_ID'), r.get('TEAM_NAME', 'Ukendt'))
            row_data = {"Hold": t_name, "TEAM_ID": r.get('TEAM_ID')}
            for label, col, _, _, _, _ in METRIC_DEFS:
                row_data[col] = r.get(col, pd.NA)
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
                    val = r.get(col, pd.NA)
                    row_disp[label] = safe_val(val, decimals, suffix)
                display_rows.append(row_disp)
            
            df_cat = pd.DataFrame(display_rows).sort_values("Hold").set_index("Hold")
            st.dataframe(df_cat, use_container_width=True, height=470, hide_index=False)
        return

    # --- 6. ENKELT HOLD-VISNING ---
    row_match = df[df['TEAM_ID'] == target_uuid]
    if row_match.empty:
        st.warning(f"Ingen data fundet for {valgt_navn}.")
        return
    row = row_match.iloc[0]

    goals_val = row.get('GOALS', 0)
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
            <div class="stat-line">• {get_rank('GOALS')} flest mål scoret ({int(row.get('GOALS', 0))})</div>
            <div class="stat-line">• {get_rank('XG')} højeste expected goals ({row.get('XG', 0):.1f} xG)</div>
            <div class="stat-line">• Forskel: {row.get('GOALS', 0) - row.get('XG', 0):.1f} mål vs xG</div>
            <div class="stat-line">• {get_rank('SHOTS_TOTAL')} flest skud i alt ({int(row.get('SHOTS_TOTAL', 0))})</div>
            <div class="stat-line">• Skudpræcision: {safe_val(row.get('SHOT_ACCURACY', 0), suffix='%')}</div>
            <div class="conclusion-text">Konklusion – {valgt_navn} {præstation_tekst} med {goals_val:.0f} mål mod {xg_val:.1f} xG.</div>
        </div>
        """, unsafe_allow_html=True)

    with col1:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Opbygningsspil</div>
            <div class="stat-line">• {get_rank('POSS')} højeste boldbesiddelse ({row.get('POSS', 0):.1f}%)</div>
            <div class="conclusion-text">Konklusion – Opbygningsstatistikker indlæst.</div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
