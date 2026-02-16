import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from mplsoccer import VerticalPitch
import seaborn as sns
import matplotlib.pyplot as plt

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
    
    # Dit query med store bogstaver for at matche Snowflake output
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
    st.markdown("### 🛡️ Taktisk Modstanderanalyse (HIF Data)")
    
    # --- INDLÆS LOKALE FILER ---
    try:
        # Vi indlæser dine CSV'er
        df_players = pd.read_csv("data/players.csv")
        # For teams.csv: Da dit eksempel ser lidt sammenflettet ud, 
        # antager vi her, at du har kolonnerne TEAM_WYID og TEAMNAME
        df_teams = pd.read_csv("data/teams.csv") 
    except Exception as e:
        st.error(f"Fejl ved indlæsning af CSV-filer: {e}")
        return

    # Hent data fra Snowflake
    st.sidebar.header("Analyse Filter")
    season_input = st.sidebar.number_input("Sæson ID", value=191807)
    
    with st.spinner("Henter live data fra Snowflake..."):
        df_live = hent_taktisk_data(season_input)

    if df_live.empty:
        st.warning("Ingen data fundet.")
        return

    # --- OVERSÆTTELSE (MERGE) ---
    # 1. Tilføj spillernavne (NAVN fra players.csv)
    df_merged = df_live.merge(
        df_players[['PLAYER_WYID', 'NAVN', 'TEAMNAME']], 
        on='PLAYER_WYID', 
        how='left'
    )
    
    # 2. Tilføj holdnavne (Hvis TEAM_WYID findes i teams.csv)
    # Hvis din teams.csv har TEAM_WYID og TEAMNAME:
    if 'TEAM_WYID' in df_teams.columns:
        df_merged = df_merged.merge(
            df_teams[['TEAM_WYID', 'TEAMNAME']], 
            on='TEAM_WYID', 
            how='left',
            suffixes=('', '_team_file')
        )

    # --- VISNING ---
    # Brug TEAMNAME fra merge eller TEAMNAME fra players.csv som fallback
    hold_navn_col = 'TEAMNAME' if 'TEAMNAME' in df_merged.columns else 'TEAM_WYID'
    hold_liste = sorted(df_merged[hold_navn_col].dropna().unique())
    
    valgt_hold = st.sidebar.selectbox("Vælg Hold", hold_liste)
    hold_data = df_merged[df_merged[hold_navn_col] == valgt_hold]

    # Nøgletal
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Aktioner", len(hold_data))
    col_m2.metric("Egne Skud", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot']))
    col_m3.metric("Skud imod", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot_against']))
    
    st.divider()

    # Baner
    col_pass, col_shot, col_against = st.columns(3)
    pitch = VerticalPitch(pitch_type='wyscout', pitch_color='white', line_color='#555555', linewidth=1.5)

    plot_configs = [
        ('pass', '🔥 Offensive Afleveringer', 'Reds', col_pass),
        ('shot', '🎯 Egne Afslutninger', 'YlOrBr', col_shot),
        ('shot_against', '⚠️ Skud Imod', 'Purples', col_against)
    ]

    for p_type, title, cmap, col in plot_configs:
        with col:
            st.caption(title)
            fig, ax = pitch.draw(figsize=(4, 6))
            data = hold_data[hold_data['PRIMARYTYPE'] == p_type]
            
            if not data.empty:
                sns.kdeplot(x=data['LOCATIONY'], y=data['LOCATIONX'], fill=True, 
                            alpha=.6, cmap=cmap, ax=ax, clip=((0, 100), (0, 100)), linewidths=0)
                
                if p_type != 'pass':
                    pitch.scatter(data.LOCATIONX, data.LOCATIONY, s=100, 
                                  color='white', edgecolors='black', ax=ax, alpha=0.8)
            st.pyplot(fig)

    # --- TOP SPILLERE LISTE ---
    if st.checkbox("Vis spillere bag aktionerne"):
        st.subheader(f"Profilerede aktioner for {valgt_hold}")
        top_spillere = hold_data.groupby(['NAVN', 'PRIMARYTYPE']).size().reset_index(name='Antal')
        st.dataframe(top_spillere.sort_values('Antal', ascending=False), use_container_width=True)

if __name__ == "__main__":
    vis_side()
