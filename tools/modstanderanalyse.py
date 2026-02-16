import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from mplsoccer import VerticalPitch
import seaborn as sns
import matplotlib.pyplot as plt
import os

# --- 1. FORBINDELSESFUNKTION (RSA) ---
def get_snowflake_connection():
    try:
        p_key_pem = st.secrets["connections"]["snowflake"]["private_key"]
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode(),
            password=None, 
            backend=default_backend()
        )
        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return snowflake.connector.connect(
            user=st.secrets["connections"]["snowflake"]["user"],
            account=st.secrets["connections"]["snowflake"]["account"],
            private_key=p_key_der,
            warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
            database=st.secrets["connections"]["snowflake"]["database"],
            schema=st.secrets["connections"]["snowflake"]["schema"],
            role=st.secrets["connections"]["snowflake"]["role"]
        )
    except Exception as e:
        st.error(f"Snowflake Forbindelsesfejl: {e}")
        return None

# --- 2. DATA-HENTNING FRA SNOWFLAKE ---
@st.cache_data(ttl=3600)
def hent_taktisk_data(season_id=191807):
    conn = get_snowflake_connection()
    if not conn:
        return pd.DataFrame()
    
    query = f"""
    SELECT 
        c.LOCATIONX, c.LOCATIONY, c.PRIMARYTYPE,
        m.MATCHLABEL, m.DATE, e.TEAM_WYID, c.PLAYER_WYID
    FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
    JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
    JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
    WHERE m.season_wyid = {season_id}
    AND (
        c.PRIMARYTYPE IN ('shot', 'shot_against') 
        OR 
        (c.PRIMARYTYPE = 'pass' AND c.LOCATIONX > 60)
    );
    """
    try:
        df = pd.read_sql(query, conn)
        df.columns = [col.upper() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Fejl ved kørsel af query: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# --- 3. HOVEDSIDE ---
def vis_side():
    st.markdown("### 🛡️ Taktisk Modstanderanalyse")
    
    # --- INDLÆS LOKALE FILER TIL OVERSÆTTELSE ---
    try:
        df_teams = pd.read_csv("data/teams.csv") # Antager kolonner: wyId, officialName
        df_players = pd.read_csv("data/players.csv") # Antager kolonner: wyId, shortName
    except Exception as e:
        st.warning(f"Kunne ikke indlæse oversættelsesfiler: {e}")
        df_teams = pd.DataFrame()
        df_players = pd.DataFrame()

    # Hent data fra Snowflake
    st.sidebar.header("Indstillinger")
    season_input = st.sidebar.number_input("Sæson ID", value=191807)
    
    with st.spinner("Henter data fra Snowflake..."):
        df = hent_taktisk_data(season_input)

    if df.empty:
        st.warning("Ingen data fundet for denne sæson.")
        return

    # --- OVERSÆTTELSE (MERGE) ---
    if not df_teams.empty:
        # Merge holdnavne (oversæt TEAM_WYID til officialName)
        df = df.merge(df_teams[['wyId', 'officialName']], left_on='TEAM_WYID', right_on='wyId', how='left')
    
    if not df_players.empty:
        # Merge spillernavne (oversæt PLAYER_WYID til shortName)
        df = df.merge(df_players[['wyId', 'shortName']], left_on='PLAYER_WYID', right_on='wyId', how='left')

    try:
        # Valg af hold i sidebar (nu med navne hvis de findes)
        hold_liste = df['officialName'].dropna().unique() if 'officialName' in df.columns else df['TEAM_WYID'].unique()
        valgt_hold = st.sidebar.selectbox("Vælg Hold", hold_liste)
        
        # Filtrer data på det valgte hold
        if 'officialName' in df.columns:
            hold_data = df[df['officialName'] == valgt_hold]
        else:
            hold_data = df[df['TEAM_WYID'] == valgt_hold]

        # Vis nøgletal
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Aktioner", len(hold_data))
        col_m2.metric("Egne Skud", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot']))
        col_m3.metric("Skud imod", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot_against']))
        
        st.divider()

        # Baner og visualisering
        col_pass, col_shot, col_against = st.columns(3)
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='white', line_color='#555555')

        # Tegn baner (samme logik som før, men nu med hold-specifik data)
        types = [('pass', '🔥 Pasninger (>60m)', 'Reds', col_pass),
                 ('shot', '🎯 Egne Afslutninger', 'YlOrBr', col_shot),
                 ('shot_against', '⚠️ Modstanderens Skud', 'Purples', col_against)]

        for p_type, title, cmap, col in types:
            with col:
                st.caption(title)
                fig, ax = pitch.draw(figsize=(4, 6))
                data = hold_data[hold_data['PRIMARYTYPE'] == p_type]
                if not data.empty:
                    sns.kdeplot(x=data['LOCATIONY'], y=data['LOCATIONX'], fill=True, 
                                alpha=.6, cmap=cmap, ax=ax, clip=((0, 100), (0, 100)))
                    if p_type != 'pass':
                        pitch.scatter(data.LOCATIONX, data.LOCATIONY, s=80, ax=ax, edgecolors='black')
                st.pyplot(fig)

    except Exception as e:
        st.error(f"Fejl ved behandling af data: {e}")

if __name__ == "__main__":
    vis_side()
