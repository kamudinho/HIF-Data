#HIF-Data/data/sql/skud_data.py
"""
Skud-/xG-data til leagueshots.py. Optimeret til at matche
officielle Opta-matchstats og undgå divergens.

RETTET: EVENT_TYPEID = 16 (Goal) udelukkede tidligere ikke selvmål
(qualifier 28) - se den samme fejl i liga_spillere.py for forklaring.
Et selvmål har ingen reel skudposition eller xG i Optas data (derfor
faldt den altid tilbage til xg_raw = 0.05), saa den udelukkes nu helt
fra skudkortet i stedet for at staa som spillerens eget skud/maal.
Mønsteret (LEFT JOIN paa qualifier 28, WHERE ... IS NULL) er det samme
som allerede brugt korrekt i kampe.py's CalculatedSubGoals.
"""

import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.players.player_mapping import player_mapping
from data.sql.db_config import DB


@st.cache_data(ttl=3600)
def load_league_data(liga_uuid):
    conn = _get_snowflake_conn()
    if not conn or not liga_uuid:
        return pd.DataFrame()

    sql = f"""
        WITH CleanQualifiers AS (
            -- Henter xG (QID 321) og sikrer én værdi pr event uden duplikering
            SELECT EVENT_OPTAUUID, MAX(TRY_CAST(QUALIFIER_VALUE AS FLOAT)) as XG_VAL
            FROM {DB}.OPTA_QUALIFIERS
            WHERE QUALIFIER_QID = 321
            GROUP BY EVENT_OPTAUUID
        ),
        OwnGoals AS (
            -- Selvmål (qualifier 28) - udelukkes fra skudkortet, da de ikke
            -- er et reelt skudforsøg fra spilleren og aldrig har en xG-værdi.
            SELECT DISTINCT EVENT_OPTAUUID
            FROM {DB}.OPTA_QUALIFIERS
            WHERE QUALIFIER_QID = 28
        ),
        PlayerNames AS (
            SELECT
                PLAYER_OPTAUUID,
                MAX(FIRST_NAME)      AS FIRST_NAME,
                MAX(LAST_NAME)       AS LAST_NAME,
                MAX(SHORT_LAST_NAME) AS SHORT_LAST_NAME,
                MAX(MATCH_NAME)      AS MATCH_NAME
            FROM {DB}.OPTA_MATCH_LINEUPS
            WHERE FIRST_NAME IS NOT NULL
            GROUP BY PLAYER_OPTAUUID
        )
        SELECT DISTINCT
            e.EVENT_OPTAUUID as event_optauuid,
            e.MATCH_OPTAUUID as match_optauuid,
            e.PLAYER_OPTAUUID as player_optauuid,
            e.EVENT_CONTESTANT_OPTAUUID as event_contestant_optauuid,
            e.EVENT_TYPEID as event_typeid,
            e.EVENT_X as event_x,
            e.EVENT_Y as event_y,
            e.EVENT_OUTCOME as event_outcome,
            e.EVENT_TIMESTAMP as event_timestamp,
            COALESCE(q.XG_VAL, 0.05) as xg_raw,
            pn.FIRST_NAME as first_name,
            pn.LAST_NAME as last_name,
            pn.SHORT_LAST_NAME as short_last_name,
            pn.MATCH_NAME as match_name,
            TRIM(COALESCE(pn.FIRST_NAME, '')) || ' ' || TRIM(COALESCE(pn.LAST_NAME, '')) as full_player_name
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        LEFT JOIN CleanQualifiers q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN OwnGoals og ON e.EVENT_OPTAUUID = og.EVENT_OPTAUUID
        LEFT JOIN PlayerNames pn ON e.PLAYER_OPTAUUID = pn.PLAYER_OPTAUUID
        WHERE m.TOURNAMENTCALENDAR_OPTAUUID = '{liga_uuid}'
          -- Præcis afgrænsning af skud (13=Miss, 14=Post, 15=Saved, 16=Goal)
          -- og frasortering af eventuelle duplikerede hændelses-id'er
          AND e.EVENT_TYPEID IN (13, 14, 15, 16)
          AND e.EVENT_OPTAUUID IS NOT NULL
          AND og.EVENT_OPTAUUID IS NULL
    """

    try:
        df = conn.query(sql) if hasattr(conn, "query") else pd.read_sql(sql, conn)
        if df is not None and not df.empty:
            df.columns = [c.upper() for c in df.columns]
            # Fjern evt. dubletter på selve event-uuid'et for en sikkerheds skyld
            df = df.drop_duplicates(subset=["EVENT_OPTAUUID"])
            df = resolve_player_names(df, conn)
            return df
        return pd.DataFrame()
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
