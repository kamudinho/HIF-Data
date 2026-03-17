import streamlit as st
import pandas as pd
from datetime import datetime

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_final_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Hent metadata for sæsonens kampe
        query_meta = f"""
        SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND "DATE" >= '2025-07-01'
          AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
        """
        df_meta = conn.query(query_meta)
        
        if df_meta.empty:
            return df_meta, pd.DataFrame()
            
        m_ids = tuple(df_meta['MATCH_SSIID'].tolist())
        formatted_ids = ','.join([f"'{i}'" for i in m_ids])

        # 2. Vi henter ALT (*) for at undgå "Invalid Identifier" fejl. 
        # Så sorterer vi i kolonnerne nede i Python i stedet.
        query_main = f"""
        SELECT *
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        return df_meta, conn.query(query_main)

    df_meta, df_raw = get_final_data()

    if df_raw.empty:
        st.warning("Ingen data fundet for de valgte kampe.")
        return

    # --- KOLONNE-MAPPING (Her løser vi navne-problemet) ---
    # Vi kigger efter de kolonner der findes i dit dump
    cols = df_raw.columns.tolist()
    
    # Vi finder de rigtige navne uanset om de er med/uden underscores
    col_dist = next((c for c in cols if "DISTANCE" in c.upper() and "PERCENT" not in c.upper()), "DISTANCE")
    col_hsr = next((c for c in cols if "HIGHSPEEDRUNNING" in c.upper().replace("_","")), None)
    col_spr = next((c for c in cols if "HIGHSPEEDSPRINTING" in c.upper().replace("_","")), None)
    col_top = next((c for c in cols if "TOP_SPEED" in c.upper() or "TOPSPEED" in c.upper()), "TOP_SPEED")

    # Beregn HI_RUN (High Speed Running + Sprinting)
    if col_hsr and col_spr:
        df_raw['HI_RUN'] = df_raw[col_hsr] + df_raw[col_spr]
    else:
        df_raw['HI_RUN'] = 0

    # Identificer Hvidovre IF baseret på TEAM_SSIID
    target_id = HIF_SSIID.lower().strip()
    df_raw['Hold'] = df_raw['TEAM_SSIID'].astype(str).str.lower().str.strip().apply(
        lambda x: "Hvidovre IF" if x == target_id else "Modstander"
    )

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # Sæson-total (Kun HIF spillere i de valgte kampe)
        df_hif = df_raw[df_raw['Hold'] == "Hvidovre IF"].copy()
        
        summary = df_hif.groupby('PLAYER_NAME').agg({
            'MATCH_SSIID': 'nunique',
            col_dist: 'sum',
            'HI_RUN': 'sum',
            col_top: 'max'
        }).reset_index().sort_values(col_dist, ascending=False)

        st.dataframe(
            summary, 
            column_config={
                "PLAYER_NAME": "Spiller",
                "MATCH_SSIID": "Kampe",
                col_dist: st.column_config.NumberColumn("Total Meter", format="%d"),
                "HI_RUN": st.column_config.NumberColumn("HI Meter", format="%d"),
                col_top: st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            use_container_width=True, hide_index=True,
            height=(len(summary) + 1) * 35 + 5
        )

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_raw.groupby('PLAYER_NAME')[col_top].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_raw.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        df_hif_m = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_m['LABEL'] = df_hif_m['DATE'].astype(str) + " - " + df_hif_m['DESCRIPTION']
        
        if not df_hif_m.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_m['LABEL'].unique(), label_visibility="collapsed")
            m_id = df_hif_m[df_hif_m['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_raw[df_raw['MATCH_SSIID'] == m_id].sort_values(by=['Hold', col_dist], ascending=[False, False])
            
            st.dataframe(
                df_match[['PLAYER_NAME', 'Hold', col_dist, 'HI_RUN', col_top]], 
                use_container_width=True, hide_index=True,
                height=(len(df_match) + 1) * 35 + 5
            )
