# utils/data/data_load.py
import os
import concurrent.futures
import streamlit as st
import pandas as pd
from datetime import datetime
import snowflake.connector

# Import fra dine mapper
from utils.data.sql.wy_queries import get_wy_queries
from utils.utils.positional_helper import beregn_primaere_positioner, berig_med_spillernavne

DB = "KLUB_HVIDOVREIF.AXIS"
BILLEDE_CACHE_TTL = 180 * 24 * 3600  # 180 dage


# --- SNOWFLAKE FORBINDELSE & PARALLELLITET ---
@st.cache_resource
def _connect():
    """Opretter og cacher den primære Snowflake-forbindelse."""
    return snowflake.connector.connect(
        account=st.secrets["connections"]["snowflake"]["account"],
        user=st.secrets["connections"]["snowflake"]["user"],
        password=st.secrets["connections"]["snowflake"]["password"],
        warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
        database=st.secrets["connections"]["snowflake"]["database"],
        schema=st.secrets["connections"]["snowflake"]["schema"],
        role=st.secrets["connections"]["snowflake"]["role"]
    )


def _get_snowflake_conn(force_new=False):
    """
    Returnerer en forbindelse. Hvis force_new er True, oprettes en ny 
    forbindelse, hvilket er nødvendigt for ægte parallelitet i tråde.
    """
    if force_new:
        return snowflake.connector.connect(
            account=st.secrets["connections"]["snowflake"]["account"],
            user=st.secrets["connections"]["snowflake"]["user"],
            password=st.secrets["connections"]["snowflake"]["password"],
            warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
            database=st.secrets["connections"]["snowflake"]["database"],
            schema=st.secrets["connections"]["snowflake"]["schema"],
            role=st.secrets["connections"]["snowflake"]["role"]
        )
    return _connect()


def _rens_og_udtræk_id(val):
    """Sikrer at ID'er renses for bogstaver (f.eks. 'M') og kun returnerer cifre som heltal."""
    if pd.isna(val) or str(val).strip() in ["", "nan", "None", "0", "0.0"]:
        return None
    clean_val = ''.join(filter(str.isdigit, str(val)))
    if not clean_val:
        return None
    try:
        return int(clean_val.split('.')[0])
    except ValueError:
        return None


def _cache_filsti(uge_id, mappe="utils/data"):
    """Filnavn med ISO-ÅR + uge, så 2026 og 2027 aldrig kolliderer."""
    iso_aar = datetime.now().isocalendar()[0]
    return os.path.join(mappe, f"cache_{iso_aar}_uge_{uge_id}.pkl")


def _beskaer_cache_filer(mappe="utils/data", behold=4):
    """Rydder gamle uge-cachefiler. Kaldes EFTER den nye fil er skrevet."""
    try:
        if not os.path.exists(mappe):
            return
        cache_filer = [
            os.path.join(mappe, f)
            for f in os.listdir(mappe)
            if f.startswith("cache_") and f.endswith(".pkl")
        ]
        cache_filer.sort(key=os.path.getmtime, reverse=True)
        for gammel_fil in cache_filer[behold:]:
            try:
                os.remove(gammel_fil)
            except Exception:
                pass
    except Exception:
        pass


def _opret_ny_forbindelse():
    """ÉN NY Snowflake-forbindelse pr. query — kræves for ægte parallelitet."""
    return _get_snowflake_conn(force_new=True)


def _fetch_parallel(query_jobs: dict) -> dict:
    """Kører flere Snowflake-queries parallelt (én forbindelse pr. query)."""
    results = {}

    def _run(sql):
        conn = _opret_ny_forbindelse()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            df = cur.fetch_pandas_all()
            return df
        finally:
            cur.close()
            conn.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(query_jobs))) as pool:
        futures = {navn: pool.submit(_run, sql) for navn, sql in query_jobs.items()}
        for navn, fut in futures.items():
            try:
                results[navn] = fut.result()
            except Exception as e:
                st.error(f"Fejl i parallel query ({navn}): {e}")
                results[navn] = pd.DataFrame()
    return results


@st.cache_data(ttl=BILLEDE_CACHE_TTL, show_spinner=False)
def hent_profilbillede(player_wyid):
    pid = _rens_og_udtræk_id(player_wyid)
    if not pid:
        return None
    conn = _get_snowflake_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID = {pid}")
        df = cur.fetch_pandas_all()
        if df is None or df.empty or "IMAGEDATAURL" not in df.columns:
            return None
        val = df["IMAGEDATAURL"].iloc[0]
        return val if pd.notna(val) else None
    except Exception:
        return None
    finally:
        cur.close()


def load_local_players():
    """Henter lokale spillere (f.eks. fra en lokal CSV-fil eller database)."""
    try:
        path = os.path.join(os.getcwd(), 'utils', 'data', 'csv', 'local_players.csv')
        if os.path.exists(path):
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=600)
def get_squad_only():
    """LYNHURTIG indlæsning til trup-oversigten (kun lokal data)."""
    df_local = load_local_players()
    try:
        path = os.path.join(os.getcwd(), 'utils', 'data', 'csv', 'scouting_db.csv')
        scout_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
    except Exception:
        scout_df = pd.DataFrame()
    return {"players": df_local, "scout_reports": scout_df}


def _indlaes_lokal_data():
    """Lokale spillere + scoutrapporter."""
    df_local = load_local_players()
    try:
        path = os.path.join(os.getcwd(), 'utils', 'data', 'csv', 'scouting_db.csv')
        scout_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
    except Exception:
        scout_df = pd.DataFrame()
    return df_local, scout_df


def _opsaml_relevante_ids(df_local, scout_df):
    """ID-opsamling med sikker rensning mod bogstaver."""
    alle_ids = []
    for df in [df_local, scout_df]:
        if df is None or df.empty:
            continue
        for col in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID']:
            if col in df.columns:
                ids = df[col].apply(_rens_og_udtræk_id).dropna().unique().tolist()
                alle_ids.extend(ids)
    return sorted(set(int(x) for x in alle_ids if x))


@st.cache_data
def get_scouting_package(uge_id):
    """
    DEN TUNGE PAKKE: Snowflake (parallelt), karriere, stats og positioner.
    """
    fil_sti = _cache_filsti(uge_id, mappe="utils/data")

    if os.path.exists(fil_sti):
        try:
            return pd.read_pickle(fil_sti)
        except Exception:
            pass

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return {}

    queries = get_wy_queries("", "")
    df_local, scout_df = _indlaes_lokal_data()
    all_relevant_ids = _opsaml_relevante_ids(df_local, scout_df)

    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()
    df_wyscout_search = pd.DataFrame()
    df_adv = pd.DataFrame()
    df_primaer_positioner = pd.DataFrame()
    hentning_ok = True

    try:
        # A. Hent hoveddata
        cur = conn.cursor()
        cur.execute(queries["players"])
        df_wyscout_search = cur.fetch_pandas_all()
        cur.close()

        # B. Parallelle forespørgsler
        if all_relevant_ids:
            id_str = f"({all_relevant_ids[0]})" if len(all_relevant_ids) == 1 else str(tuple(all_relevant_ids))

            career_q = queries["player_career"]
            career_q = (career_q.replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY")
                        if "ORDER BY" in career_q
                        else career_q + f" WHERE pc.PLAYER_WYID IN {id_str}")

            adv_q = queries["player_stats_total"]
            adv_q = (adv_q + f" AND pt.PLAYER_WYID IN {id_str}" if "WHERE" in adv_q
                     else adv_q + f" WHERE pt.PLAYER_WYID IN {id_str}")

            pos_q = queries["position_base"].format(id_list=id_str)

            par = _fetch_parallel({"career": career_q, "adv": adv_q, "pos": pos_q})
            df_career = par["career"]
            df_adv = par["adv"]

            try:
                df_position_base = par["pos"]
                if df_position_base is not None and not df_position_base.empty:
                    df_primaer_positioner = beregn_primaere_positioner(df_position_base)
                    df_primaer_positioner = berig_med_spillernavne(df_primaer_positioner, df_wyscout_search)
            except Exception as pos_e:
                st.warning(f"Kunne ikke beregne primær-positioner: {pos_e}")
                df_primaer_positioner = pd.DataFrame()

        for df in [df_sql_p, df_career, df_wyscout_search, df_adv]:
            if df is not None and not df.empty:
                df.columns = [str(c).upper().strip() for c in df.columns]
                for col in ['PLAYER_WYID', 'COMPETITION_WYID']:
                    if col in df.columns:
                        df[col] = df[col].astype(str).str.split('.').str[0].str.strip()

    except Exception as e:
        hentning_ok = False
        st.error(f"SQL Fejl i Scouting Load: {e}")

    data_pakke = {
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search,
        "players": df_wyscout_search,
        "local_players": df_local,
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_adv,
        "primaer_positioner": df_primaer_positioner,
    }

    if hentning_ok:
        try:
            os.makedirs("utils/data", exist_ok=True)
            pd.to_pickle(data_pakke, fil_sti)
            _beskaer_cache_filer(mappe="utils/data", behold=4)
        except Exception:
            pass

    return data_pakke
