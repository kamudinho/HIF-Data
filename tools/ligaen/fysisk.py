import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"
SEASON_NAME = "2025/2026"

def vis_side(conn, name_map=None):
    if name_map is None: name_map = {}

    # --- TRIN 1: HENT METADATA (KUN DENNE TURNERING OG SÆSON) ---
    @st.cache_data(ttl=600)
    def get_matches():
        query = f"""
        SELECT 
            DATE,
            HOME_SSIID,
            AWAY_SSIID,
            DESCRIPTION,
            MATCH_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}'
          AND YEAR = '2025'
        ORDER BY DATE DESC
        """
        return conn.query(query)

    # --- TRIN 2: HENT FYSISK DATA ---
    @st.cache_data(ttl=600)
    def get_all_phys():
        query = "SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS"
        df = conn.query(query)
        df['HI_RUN'] = df['HIGH SPEED RUNNING'] + df['SPRINTING']
        df['Spiller'] = df['PLAYER_NAME']
        return df

    df_meta = get_matches()
    df_all_phys = get_all_phys()

    if df_meta.empty:
        st.warning("Ingen kampdata fundet for den valgte turnering og saeson.")
        return

    # --- TABS ---
    t1, t2, t3 = st.tabs(["Saeson Oversigt (HIF)", "Top 5 Liga", "Kampoversigt"])

    # TAB 1: HVIDOVRE SÆSON-TOTALER
    with t1:
        st.markdown(f"### Hvidovre-spillere samlet for saesonen {SEASON_NAME}")
        
        # 1. Find alle kampe Hvidovre har spillet
        hif_match_ids = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)]['MATCH_SSIID'].unique()
        
        # 2. Hent data for de kampe
        df_hif_raw = df_all_phys[df_all_phys['MATCH_SSIID'].isin(hif_match_ids)]

        # 3. FILTRERING: Her skal vi kun have HIF spillere. 
        # Da vi ikke har en TEAM_SSIID i tabellen, filtrerer vi her på de spillere, 
        # der optræder i din PLAYER_MAP eller en liste over HIF-navne.
        # Hvis du ikke har en liste, kan vi filtrere på TEAM_SSIID hvis den findes i df_all_phys
        
        if 'TEAM_SSIID' in df_hif_raw.columns:
            df_hif_only = df_hif_raw[df_hif_raw['TEAM_SSIID'] == HIF_SSIID]
        else:
            # Alternativ: Hvis vi ikke har TEAM_SSIID, viser vi alle, 
            # men du kan tilføje en liste over efternavne her:
            df_hif_only = df_hif_raw # Midlertidig indtil TEAM_SSIID bekræftes

        df_hif_season = df_hif_only.groupby('Spiller').agg({
            'MINUTES': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'TOP_SPEED': 'max',
            'SPRINTING': 'sum'
        }).reset_index()

        st.dataframe(
            df_hif_season.sort_values('DISTANCE', ascending=False),
            column_config={
                "DISTANCE": st.column_config.NumberColumn("Total Distance (m)", format="%.0f"),
                "HI_RUN": "Total HI (m)",
                "TOP_SPEED": "Max Topfart",
                "SPRINTING": "Total Sprint (m)"
            },
            use_container_width=True, hide_index=True
        )

    # TAB 2: TOP 5 LIGA (KUN DENNE TURNERING OG SÆSON)
    with t2:
        st.markdown(f"### Top 5 paa tvaers af ligaen (Saeson)")
        # Vi filtrerer df_all_phys så den kun indeholder spillere fra kampene i df_meta
        df_liga_phys = df_all_phys[df_all_phys['MATCH_SSIID'].isin(df_meta['MATCH_SSIID'].unique())]
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Hojeste Topfart**")
            st.table(df_liga_phys.groupby('Spiller')['TOP_SPEED'].max().nlargest(5).reset_index().set_index('Spiller'))
            st.write("**Total Distance (m)**")
            st.table(df_liga_phys.groupby('Spiller')['DISTANCE'].sum().nlargest(5).reset_index().set_index('Spiller'))
        with c2:
            st.write("**Total HI-lob (m)**")
            st.table(df_liga_phys.groupby('Spiller')['HI_RUN'].sum().nlargest(5).reset_index().set_index('Spiller'))
            st.write("**Total Sprint (m)**")
            st.table(df_liga_phys.groupby('Spiller')['SPRINTING'].sum().nlargest(5).reset_index().set_index('Spiller'))

    # TAB 3: KAMPOVERSIGT
    with t3:
        def get_team_name(ssiid):
            for name, info in TEAMS.items():
                if info.get('ssid') == ssiid: return name
            return ssiid[:5]

        # Kun HIF kampe i dropdown
        df_hif_meta = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_meta['DISPLAY'] = df_hif_meta['DATE'].astype(str) + ": " + df_hif_meta['DESCRIPTION']
        
        valgt_kamp = st.selectbox("Vaelg kamp:", df_hif_meta['DISPLAY'])
        valgt_match_id = df_hif_meta[df_hif_meta['DISPLAY'] == valgt_kamp]['MATCH_SSIID'].values[0]
        
        row = df_hif_meta[df_hif_meta['MATCH_SSIID'] == valgt_match_id].iloc[0]
        hold_valg = st.selectbox("Vaelg hold:", ["Begge hold", get_team_name(row['HOME_SSIID']), get_team_name(row['AWAY_SSIID'])])
        
        df_match = df_all_phys[df_all_phys['MATCH_SSIID'].str.strip() == valgt_match_id.strip()]
        
        st.dataframe(
            df_match[['Spiller', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            use_container_width=True, hide_index=True
        )
