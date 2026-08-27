from io import BytesIO
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from PIL import Image
import streamlit as st
from data.data_load import _get_snowflake_conn
from data.players.player_mapping import player_mapping
from data.utils.team_mapping import COMPETITIONS, SEASONS, TEAM_COLORS, TEAMS
from utils.pitches import get_boundaries, get_pitch

# Importér eksisterende moduler og funktioner
from data.data_load import _get_snowflake_conn
from data.players.player_mapping import player_mapping
from data.utils.team_mapping import COMPETITIONS, SEASONS, TEAM_COLORS, TEAMS
from utils.pitches import get_boundaries, get_pitch

# --- KONFIGURATION (Hvidovre-app værdier) ---
HIF_RED = "#cc0000"
DB = "KLUB_HVIDOVREIF.AXIS"

# --- ZONE DEFINITIONER ---
ZONE_BOUNDARIES = get_boundaries()


@st.cache_data(ttl=3600)
def load_league_data(liga_uuid):
    conn = _get_snowflake_conn()
    if not conn or not liga_uuid:
        return pd.DataFrame()

    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{liga_uuid}'"

    sql = f"""
        SELECT 
            e.*, 
            TRIM(l.FIRST_NAME) || ' ' || TRIM(l.LAST_NAME) as FULL_PLAYER_NAME,
            q.QUALIFIER_VALUE as XG_RAW 
        FROM {DB}.OPTA_EVENTS e 
        LEFT JOIN (
            SELECT DISTINCT MATCH_OPTAUUID, PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME 
            FROM {DB}.OPTA_MATCH_LINEUPS 
            WHERE FIRST_NAME IS NOT NULL AND LAST_NAME IS NOT NULL
        ) l 
            ON e.MATCH_OPTAUUID = l.MATCH_OPTAUUID AND e.PLAYER_OPTAUUID = l.PLAYER_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 321
        WHERE e.EVENT_TYPEID IN (13,14,15,16) 
        AND e.MATCH_OPTAUUID IN ({match_sql})
    """

    try:
        df = conn.query(sql) if hasattr(conn, "query") else pd.read_sql(sql, conn)
        df.columns = [c.upper() for c in df.columns]

        df = resolve_player_names(df, conn)

        return df
    except Exception as e:
        st.error(f"Fejl ved indlæsning af data fra Snowflake: {e}")
        return pd.DataFrame()


def resolve_player_names(df, conn=None):
    if df.empty or "PLAYER_OPTAUUID" not in df.columns:
        if "PLAYER_NAME" not in df.columns:
            df["PLAYER_NAME"] = "Ukendt"
        else:
            df["PLAYER_NAME"] = df["PLAYER_NAME"].fillna("Ukendt")
        return df

    resolved = df["PLAYER_OPTAUUID"].map(player_mapping.optauuid_to_name)

    if "FULL_PLAYER_NAME" in df.columns:
        resolved = resolved.fillna(df["FULL_PLAYER_NAME"])

    df["PLAYER_NAME"] = resolved

    missing_mask = df["PLAYER_NAME"].isna() | (
        df["PLAYER_NAME"].astype(str).str.strip() == ""
    )
    missing_uuids = df.loc[missing_mask, "PLAYER_OPTAUUID"].dropna().unique()

    if len(missing_uuids) > 0 and conn is not None:
        for uuid in missing_uuids:
            navn = player_mapping.get_name_by_opta_uuid(uuid, conn=conn, db_name=DB)
            if navn and navn != "Ukendt":
                df.loc[df["PLAYER_OPTAUUID"] == uuid, "PLAYER_NAME"] = navn

    df["PLAYER_NAME"] = df["PLAYER_NAME"].fillna("Ukendt")
    df.loc[df["PLAYER_NAME"].astype(str).str.strip() == "", "PLAYER_NAME"] = (
        "Ukendt"
    )

    player_mapping.register_players_from_df(
        df, uuid_col="PLAYER_OPTAUUID", name_col="PLAYER_NAME"
    )

    return df


@st.cache_data(ttl=3600)
def get_logo_img(url):
    try:
        return Image.open(BytesIO(requests.get(url, timeout=5).content))
    except:
        return None


def to_metric(val, total_m):
    return val * (total_m / 100)


def map_to_zone(r):
    mx, my = to_metric(r["EVENT_X"], 105), to_metric(r["EVENT_Y"], 68)
    for z, b in ZONE_BOUNDARIES.items():
        if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]:
            return z
    return "Zone 8"


def draw_logo_on_pitch(ax, logo_img):
    if logo_img:
        ax_logo = ax.inset_axes([0.02, 0.89, 0.12, 0.10], transform=ax.transAxes)
        ax_logo.imshow(logo_img)
        ax_logo.axis("off")


def get_xg_color(xg_val):
    if xg_val < 0.15:
        return "#999999"  # Grå
    elif xg_val < 0.35:
        return "#2ecc71"  # Grøn
    else:
        return "#e74c3c"  # Rød


# --- MAIN APP ---
def vis_side(dp=None):
    st.markdown(
        """
    <style>
        header {visibility: hidden;}
        .main .block-container { 
            padding-top: 1rem !important; 
            padding-bottom: 3rem !important; 
            max-width: 1400px !important; 
        }
        .stat-box { 
            background-color: #f8f9fa; 
            padding: 10px !important; 
            border-radius: 5px; 
            border-left: 5px solid #cc0000; 
            margin-bottom: 15px !important; 
            display: block; 
        }
        .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; }
        .stat-value { font-size: 1.3rem; font-weight: 800; color: #1a1a1a; margin-top: 3px; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    top_col1, top_col2 = st.columns([1.5, 2.5])

    with top_col1:
        st.caption("**Afslutningsanalyse**")

    f_col1, f_col2, f_col3 = top_col2.columns(3)
    with f_col1:
        sæson_sel = st.selectbox("Sæson", list(SEASONS.keys()), index=0)

    with f_col2:
        tilgængelige_turneringer = [
            t for t in SEASONS[sæson_sel].keys() if "superliga" not in t.lower()
        ]
        if not tilgængelige_turneringer:
            tilgængelige_turneringer = list(SEASONS[sæson_sel].keys())
        turnering_sel = st.selectbox("Turnering", tilgængelige_turneringer, index=0)

    from data.utils.team_mapping import SEASON_LEAGUE_MAPPER

    teams = SEASON_LEAGUE_MAPPER.get(sæson_sel, {}).get(
        turnering_sel, sorted(list(TEAMS.keys()))
    )

    with f_col3:
        default_idx = teams.index("Hvidovre") if "Hvidovre" in teams else 0
        t_sel = st.selectbox("Hold", teams, index=default_idx)

    aktuel_liga_uuid = SEASONS[sæson_sel][turnering_sel]
    df_all = load_league_data(aktuel_liga_uuid)

    if not df_all.empty and "EVENT_CONTESTANT_OPTAUUID" in df_all.columns:
        uuid_to_name = {
            v["opta_uuid"].upper(): k for k, v in TEAMS.items() if v.get("opta_uuid")
        }
        df_all["KLUB_NAVN"] = (
            df_all["EVENT_CONTESTANT_OPTAUUID"].str.upper().map(uuid_to_name)
        )
    else:
        if not df_all.empty:
            df_all["KLUB_NAVN"] = None

    if df_all.empty or not teams or t_sel == "Der er ingen data at vise":
        st.warning("Ingen data at vise for den valgte sæson/turnering.")
        return

    df_team = df_all[df_all["KLUB_NAVN"] == t_sel].copy()
    
    # Håndter xG kolonne for holdet generelt
    if "XG_RAW" in df_team.columns:
        df_team["XG"] = pd.to_numeric(df_team["XG_RAW"], errors="coerce").fillna(0.05)
    else:
        df_team["XG"] = 0.05

    # Data for modstandere (skud imod det valgte hold i samme kampe)
    match_uuids_team = df_team["MATCH_OPTAUUID"].unique()
    df_modstander = df_all[
        (df_all["MATCH_OPTAUUID"].isin(match_uuids_team))
        & (df_all["KLUB_NAVN"] != t_sel)
    ].copy()

    if df_team.empty:
        st.warning(f"Der er ingen data at vise for {t_sel} i den valgte turnering.")
        return

    # Metrik og zoner for holdet
    df_team["X_M"] = df_team["EVENT_X"].apply(lambda x: to_metric(x, 105))
    df_team["Y_M"] = df_team["EVENT_Y"].apply(lambda y: to_metric(y, 68))
    df_team["Zone"] = df_team.apply(map_to_zone, axis=1)
    df_team["IS_DZ"] = (
        (df_team["X_M"] >= 88.5)
        & (df_team["Y_M"] >= 25.16)
        & (df_team["Y_M"] <= 42.84)
    )

    # Metrik og zoner for modstandere (skud imod)
    if not df_modstander.empty:
        df_modstander["X_M"] = df_modstander["EVENT_X"].apply(
            lambda x: to_metric(x, 105)
        )
        df_modstander["Y_M"] = df_modstander["EVENT_Y"].apply(
            lambda y: to_metric(y, 68)
        )
        df_modstander["Zone"] = df_modstander.apply(map_to_zone, axis=1)
        if "XG_RAW" in df_modstander.columns:
            df_modstander["XG"] = pd.to_numeric(
                df_modstander["XG_RAW"], errors="coerce"
            ).fillna(0.05)
        else:
            df_modstander["XG"] = 0.05

    tabs = st.tabs([
        "SPILLEROVERSIGT",
        "AFSLUTNINGER",
        "DZ-ANALYSE",
        "SKUDZONER",
        "MÅLZONER",
        "AFSLUTNINGER MOD",
    ])

    # TAB 0: SPILLEROVERSIGT
    with tabs[0]:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        p_stats = []
        for p, d in df_team.groupby("PLAYER_NAME"):
            s, m = len(d), len(d[d["EVENT_TYPEID"] == 16])
            dz_d = d[d["IS_DZ"]]
            dz_s, dz_m = len(dz_d), len(dz_d[dz_d["EVENT_TYPEID"] == 16])

            p_stats.append({
                "Spiller": p,
                "Skud": s,
                "Mål": m,
                "Konv.%": (m / s * 100 if s > 0 else 0),
                "DZ-Skud": dz_s,
                "DZ-Mål": dz_m,
                "DZ-Konv.%": (dz_m / dz_s * 100 if dz_s > 0 else 0),
                "DZ-Andel": (dz_s / s * 100 if s > 0 else 0),
            })

        df_display = pd.DataFrame(p_stats).sort_values("Konv.%", ascending=False)
        dynamic_height = (len(df_display) + 1) * 38 + 50

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=dynamic_height,
            column_config={
                "Spiller": st.column_config.TextColumn("Spiller", width="medium"),
                "DZ-Andel": st.column_config.ProgressColumn(
                    "DZ-Andel",
                    help="Andel af skud foretaget i Danger Zone",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                    width="medium",
                ),
                "Konv.%": st.column_config.NumberColumn(
                    "Konv.%", format="%.1f%%", width="small"
                ),
                "DZ-Konv.%": st.column_config.NumberColumn(
                    "DZ-Konv.%", format="%.1f%%", width="small"
                ),
            },
        )

    # TAB 1: AFSLUTNINGER
    with tabs[1]:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([2, 1])
        t_color = TEAM_COLORS.get(t_sel, {}).get("primary", HIF_RED)
        t_logo = get_logo_img(TEAMS.get(t_sel, {}).get("logo"))

        with c2:
            st.markdown("##### Filtre")
            
            # 1. Kamp-filter
            # Hent kampe hvor holdet har deltaget for at lave en pæn dropdown
            match_options = {"Alle kampe": None}
            if "MATCH_OPTAUUID" in df_team.columns:
                unique_matches = df_team["MATCH_OPTAUUID"].unique()
                for m_id in unique_matches:
                    # Prøv at finde modstander / info hvis muligt, ellers brug ID'et
                    sub_df = df_all[(df_all["MATCH_OPTAUUID"] == m_id) & (df_all["KLUB_NAVN"] != t_sel)]
                    opp_name = sub_df["KLUB_NAVN"].iloc[0] if not sub_df.empty and "KLUB_NAVN" in sub_df.columns and sub_df["KLUB_NAVN"].notna().any() else "Modstander"
                    match_options[f"Kamp mod {opp_name} ({m_id[:6]}...)"] = m_id

            kamp_sel_label = st.selectbox("Vælg kamp", list(match_options.keys()))
            valgt_kamp_uuid = match_options[kamp_sel_label]

            # Filtrer df_team baseret på valgt kamp
            d_filtered = df_team if valgt_kamp_uuid is None else df_team[df_team["MATCH_OPTAUUID"] == valgt_kamp_uuid]

            # 2. Spiller-filter
            spiller_liste = ["Alle spillere"] + sorted(d_filtered["PLAYER_NAME"].unique()) if not d_filtered.empty else ["Alle spillere"]
            p_sel = st.selectbox("Filtrer spiller", spiller_liste)
            
            if p_sel != "Alle spillere":
                d_v = d_filtered[d_filtered["PLAYER_NAME"] == p_sel]
            else:
                d_v = d_filtered

            # 3. Visningstype (Antal vs xG)
            vis_mode_afsl = st.radio("Vælg visning:", ["Antal", "xG"], index=0, key="afsl_mode")

            s, m = len(d_v), len(d_v[d_v["EVENT_TYPEID"] == 16])
            tot_xg_afsl = d_v["XG"].sum() if not d_v.empty else 0.0

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Total xG</div><div class="stat-value">{tot_xg_afsl:.2f}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Konvertering</div><div class="stat-value">{(m/s*100 if s>0 else 0):.1f}%</div></div>', unsafe_allow_html=True)

            if vis_mode_afsl == "xG":
                st.markdown("---")
                st.markdown("**Farveforklaring (xG):**")
                st.markdown(
                    "Grå = **< 0,15** (Lav kvalitet)"
                    "<br>Grøn = **0,15 - 0,35** (Medium kvalitet)"
                    "<br>Rød = **>= 0,35** (Høj kvalitet)",
                    unsafe_allow_html=True,
                )

        with c1:
            pitch, fig, ax = get_pitch("halv", t_color=t_color)
            if not d_v.empty:
                if vis_mode_afsl == "Antal":
                    colors = (d_v["EVENT_TYPEID"] == 16).map({True: t_color, False: "white"})
                    pitch.scatter(
                        d_v["X_M"],
                        d_v["Y_M"],
                        s=120,
                        c=colors,
                        edgecolors=t_color,
                        ax=ax,
                        zorder=3,
                        alpha=0.9,
                    )
                else:
                    colors = d_v["XG"].apply(get_xg_color)
                    pitch.scatter(
                        d_v["X_M"],
                        d_v["Y_M"],
                        s=140,
                        c=colors,
                        edgecolors="black",
                        ax=ax,
                        zorder=3,
                        alpha=0.85,
                    )
            draw_logo_on_pitch(ax, t_logo)
            st.pyplot(fig)

    # TAB 2: DZ-ANALYSE
    with tabs[2]:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([2, 1])
        dz_d = df_team[df_team["IS_DZ"]]
        t_color = TEAM_COLORS.get(t_sel, {}).get("primary", HIF_RED)
        t_logo = get_logo_img(TEAMS.get(t_sel, {}).get("logo"))
        with c2:
            s_dz, m_dz = len(dz_d), len(dz_d[dz_d["EVENT_TYPEID"] == 16])
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">DZ Skud</div><div'
                f' class="stat-value">{s_dz}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">DZ Mål</div><div'
                f' class="stat-value">{m_dz}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">DZ'
                f' Konv.</div><div'
                f' class="stat-value">{(m_dz/s_dz*100 if s_dz>0 else 0):.1f}%</div></div>',
                unsafe_allow_html=True,
            )
        with c1:
            pitch, fig, ax = get_pitch("halv", t_color=t_color)
            ax.add_patch(
                patches.Rectangle(
                    (25.16, 88.7),
                    17.68,
                    16.5,
                    color=t_color,
                    alpha=0.15,
                    zorder=1,
                )
            )
            pitch.scatter(
                dz_d["X_M"],
                dz_d["Y_M"],
                s=100,
                c=(dz_d["EVENT_TYPEID"] == 16).map({True: t_color, False: "white"}),
                edgecolors=t_color,
                ax=ax,
                zorder=3,
            )
            draw_logo_on_pitch(ax, t_logo)
            st.pyplot(fig)

    # TAB 3 & 4: ZONER (Skudzoner & Målzoner)
    for i, is_goal in enumerate([False, True]):
        with tabs[i + 3]:
            st.markdown(
                "<div style='margin-top: 15px;'></div>", unsafe_allow_html=True
            )
            c1, c2 = st.columns([1.6, 1])
            plot_df = df_team[df_team["EVENT_TYPEID"] == 16] if is_goal else df_team
            total_count = len(plot_df)
            t_color = TEAM_COLORS.get(t_sel, {}).get("primary", HIF_RED)
            t_logo = get_logo_img(TEAMS.get(t_sel, {}).get("logo"))

            with c2:
                st.write(f"**Zone-stats ({'Mål' if is_goal else 'Skud'})**")
                z_summary = []
                for z, b in ZONE_BOUNDARIES.items():
                    z_d = plot_df[plot_df["Zone"] == z]
                    if len(z_d) > 0:
                        top_p = z_d["PLAYER_NAME"].value_counts().idxmax()
                        z_summary.append({
                            "Zone": z,
                            "Antal": len(z_d),
                            "Andel": (
                                len(z_d) / total_count if total_count > 0 else 0
                            ),
                            "Topscorer": top_p,
                        })

                if z_summary:
                    st.dataframe(
                        pd.DataFrame(z_summary).sort_values("Antal", ascending=False),
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Andel": st.column_config.NumberColumn(format="%.1f%%")
                        },
                    )

            with c1:
                zone_counts = {
                    z: len(plot_df[plot_df["Zone"] == z])
                    for z in ZONE_BOUNDARIES.keys()
                }
                pitch, fig, ax = get_pitch(
                    "halv",
                    zone_boundaries=ZONE_BOUNDARIES,
                    zone_data=zone_counts,
                    t_color=t_color,
                )
                draw_logo_on_pitch(ax, t_logo)
                st.pyplot(fig)

    # TAB 5: AFSLUTNINGER MOD
    with tabs[5]:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([2, 1])
        t_logo = get_logo_img(TEAMS.get(t_sel, {}).get("logo"))

        with c2:
            st.markdown("##### Visningstype")
            vis_mode = st.radio(
                "Vælg visning for skud imod:", ["Antal", "xG"], index=0, key="mod_mode"
            )

            s_mod = len(df_modstander)
            m_mod = (
                len(df_modstander[df_modstander["EVENT_TYPEID"] == 16])
                if not df_modstander.empty
                else 0
            )
            tot_xg = (
                df_modstander["XG"].sum()
                if not df_modstander.empty and "XG" in df_modstander.columns
                else 0.0
            )

            st.markdown(
                "<div style='margin-top: 20px;'></div>", unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">Skud Imod</div><div'
                f' class="stat-value">{s_mod}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">Mål Imod</div><div'
                f' class="stat-value">{m_mod}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">Total xG Imod</div><div'
                f' class="stat-value">{tot_xg:.2f}</div></div>',
                unsafe_allow_html=True,
            )

            if vis_mode == "xG":
                st.markdown("---")
                st.markdown("**Farveforklaring (xG):**")
                st.markdown(
                    "Grå = **< 0,15** (Lav kvalitet)"
                    "<br>Grøn = **0,15 - 0,35** (Medium kvalitet)"
                    "<br>Rød = **>= 0,35** (Høj kvalitet)",
                    unsafe_allow_html=True,
                )

        with c1:
            pitch, fig, ax = get_pitch("halv", t_color="#333333")

            if not df_modstander.empty:
                if vis_mode == "Antal":
                    colors = (df_modstander["EVENT_TYPEID"] == 16).map(
                        {True: "#cc0000", False: "#888888"}
                    )
                    pitch.scatter(
                        df_modstander["X_M"],
                        df_modstander["Y_M"],
                        s=120,
                        c=colors,
                        edgecolors="black",
                        ax=ax,
                        zorder=3,
                        alpha=0.8,
                    )
                else:
                    colors = df_modstander["XG"].apply(get_xg_color)
                    pitch.scatter(
                        df_modstander["X_M"],
                        df_modstander["Y_M"],
                        s=140,
                        c=colors,
                        edgecolors="black",
                        ax=ax,
                        zorder=3,
                        alpha=0.85,
                    )

            draw_logo_on_pitch(ax, t_logo)
            st.pyplot(fig)


if __name__ == "__main__":
    vis_side()
