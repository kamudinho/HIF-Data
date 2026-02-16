import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from mplsoccer import VerticalPitch
import seaborn as sns
import matplotlib.pyplot as plt

# --- 1. RSA FORBINDELSE ---
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
        st.error(f"Forbindelsesfejl: {e}")
        return None

# --- 2. HENT DATA (DIN SQL) ---
@st.cache_data(ttl=3600)
def hent_taktisk_data(season_id=191807):
    conn = get_snowflake_connection()
    if not conn: return pd.DataFrame()
    
    query = f"""
    SELECT 
        c.LOCATIONX, c.LOCATIONY, c.PRIMARYTYPE,
        m.MATCHLABEL, m.DATE, e.TEAM_WYID
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
        st.error(f"SQL Fejl: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# --- 3. HOVEDSIDE ---
def vis_side():
    st.title("🛡️ Taktisk Modstanderanalyse")

    # 1. Indlæs hold-oversættelse
    try:
        # Vi forventer TEAM_WYID og TEAMNAME i din teams.csv
        df_teams = pd.read_csv("data/teams.csv")
        team_map = dict(zip(df_teams['TEAM_WYID'], df_teams['TEAMNAME']))
    except:
        team_map = {}

    # 2. Hent data
    df_live = hent_taktisk_data(191807)
    
    if not df_live.empty:
        # Map holdnavne eller brug ID som backup
        df_live['HOLD_NAVN'] = df_live['TEAM_WYID'].map(team_map).fillna(df_live['TEAM_WYID'].astype(str))
        
        # Sidebar filter
        alle_hold = sorted(df_live['HOLD_NAVN'].unique())
        valgt_hold = st.sidebar.selectbox("Vælg modstander:", alle_hold)
        
        hold_data = df_live[df_live['HOLD_NAVN'] == valgt_hold]

        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Aktioner i alt", len(hold_data))
        c2.metric("Skud", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot']))
        c3.metric("Skud imod", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot_against']))

        st.divider()

        # Baner
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='white', line_color='#555555')
        cols = st.columns(3)
        configs = [
            ('pass', 'Offensive Pasninger', 'Reds'),
            ('shot', 'Egne Skud', 'YlOrBr'),
            ('shot_against', 'Skud Imod', 'Purples')
        ]

        for i, (p_type, title, cmap) in enumerate(configs):
            with cols[i]:
                st.caption(title)
                fig, ax = pitch.draw(figsize=(4, 6))
                d = hold_data[hold_data['PRIMARYTYPE'] == p_type]
                if not d.empty:
                    sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, alpha=.5, cmap=cmap, ax=ax)
                    if p_type != 'pass':
                        pitch.scatter(d.LOCATIONX, d.LOCATIONY, s=40, edgecolors='black', ax=ax)
                st.pyplot(fig)
    else:
        st.info("Ingen data fundet. Tjek Snowflake-forbindelsen eller Sæson ID.")

if __name__ == "__main__":
    vis_side()
