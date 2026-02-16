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

# --- 2. DATA-HENTNING (DIT SQL QUERY) ---
@st.cache_data(ttl=3600) # Gemmer data i 1 time for at spare på Snowflake-credits
def hent_taktisk_data(season_id=191807):
    conn = get_snowflake_connection()
    if not conn:
        return pd.DataFrame()
    
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
        # Sørg for kolonnenavne er store bogstaver (Snowflake standard)
        df.columns = [col.upper() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Fejl ved kørsel af query: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# --- 3. HOVEDSIDE ---
def vis_side():
    st.markdown("### 🛡️ Taktisk Modstanderanalyse (Snowflake Live)")
    
    # Indlæs data fra Snowflake
    st.sidebar.header("Filter")
    season_input = st.sidebar.number_input("Sæson ID", value=191807)
    
    with st.spinner("Henter data fra Snowflake..."):
        df = hent_taktisk_data(season_input)

    if df.empty:
        st.warning("Ingen data fundet for denne sæson.")
        return

    try:
        # Sidebjælke: Vælg kamp
        valgt_kamp = st.sidebar.selectbox("Vælg Kamp", df['MATCHLABEL'].unique())
        kamp_data = df[df['MATCHLABEL'] == valgt_kamp]
        
        # 2. Overskrift og overordnede tal
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Aktioner i alt", len(kamp_data))
        col_m2.metric("Egne Skud", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']))
        col_m3.metric("Skud imod", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']))
        
        st.divider()

        # 3. Opsætning af tre kolonner til de tre baner
        col_pass, col_shot, col_against = st.columns(3)

        # Fælles Pitch-indstillinger (Wyscout bruger 0-100 koordinater)
        pitch = VerticalPitch(
            pitch_type='wyscout', pitch_color='white', 
            line_color='#555555', linewidth=1.5
        )

        # --- KOLONNE 1: PASNINGER (KUN OFFENSIVE > 60X) ---
        with col_pass:
            st.caption("🔥 Offensive Pasninger (>60m)")
            fig1, ax1 = pitch.draw(figsize=(4, 6))
            data = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            if not data.empty:
                sns.kdeplot(x=data['LOCATIONY'], y=data['LOCATIONX'], fill=True, 
                            alpha=.6, cmap='Reds', ax=ax1, clip=((0, 100), (0, 100)), linewidths=0)
                pitch.arrows(data.LOCATIONX, data.LOCATIONY, data.LOCATIONX + 2, data.LOCATIONY, 
                             width=1.5, color='#3498db', ax=ax1, alpha=0.3)
            st.pyplot(fig1)

        # --- KOLONNE 2: EGNE SKUD ---
        with col_shot:
            st.caption("🎯 Egne Afslutninger")
            fig2, ax2 = pitch.draw(figsize=(4, 6))
            data = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']
            if not data.empty:
                sns.kdeplot(x=data['LOCATIONY'], y=data['LOCATIONX'], fill=True, 
                            alpha=.6, cmap='YlOrBr', ax=ax2, clip=((0, 100), (0, 100)), linewidths=0)
                pitch.scatter(data.LOCATIONX, data.LOCATIONY, color='red', edgecolors='black', s=80, ax=ax2)
            st.pyplot(fig2)

        # --- KOLONNE 3: SKUD IMOD ---
        with col_against:
            st.caption("⚠️ Modstanderens Skud")
            fig3, ax3 = pitch.draw(figsize=(4, 6))
            data = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']
            if not data.empty:
                sns.kdeplot(x=data['LOCATIONY'], y=data['LOCATIONX'], fill=True, 
                            alpha=.6, cmap='Purples', ax=ax3, clip=((0, 100), (0, 100)), linewidths=0)
                pitch.scatter(data.LOCATIONX, data.LOCATIONY, color='purple', edgecolors='white', s=80, ax=ax3)
            st.pyplot(fig3)

    except Exception as e:
        st.error(f"Fejl ved visualisering: {e}")

if __name__ == "__main__":
    vis_side()
