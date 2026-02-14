import streamlit as st
import snowflake.connector
import os

def get_snowflake_conn():
    """Opretter forbindelse vha. dine secrets i .streamlit/secrets.toml"""
    return snowflake.connector.connect(**st.secrets["snowflake"])

def hent_match_data(event_id):
    try:
        conn = get_snowflake_conn()
        cur = conn.cursor()
        # SQL der kobler videoens EVENT_WYID til kampdata
        query = f"""
            SELECT 
                m2.TEAM_WYID as OPP_ID, 
                m1.SCORE as HOME_SCORE, 
                m2.SCORE as AWAY_SCORE, 
                m1.VENUE,
                m1.DATE
            FROM KLUB_NAESBYBOLDKLUB.AXIS.EVENTS e
            JOIN KLUB_NAESBYBOLDKLUB.AXIS.MATCH_DETAILS m1 ON e.MATCH_WYID = m1.MATCH_WYID
            JOIN KLUB_NAESBYBOLDKLUB.AXIS.MATCH_DETAILS m2 ON m1.MATCH_WYID = m2.MATCH_WYID
            WHERE e.EVENT_WYID = {event_id}
              AND m1.TEAM_WYID = 38331
              AND m2.TEAM_WYID <> 38331
        """
        cur.execute(query)
        return cur.fetchone()
    except Exception as e:
        st.error(f"Snowflake fejl: {e}")
        return None
    finally:
        if 'conn' in locals(): conn.close()

def vis_side(spillere):
    st.title("🎥 Video- & Sekvensanalyse")
    
    video_dir = "videos"
    
    if not os.path.exists(video_dir):
        st.info("Opret en mappe der hedder 'videos' og læg dine .mp4 filer derind.")
        return

    video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]

    if not video_filer:
        st.write("Ingen videoer fundet i mappen.")
        return

    # Layout: Oversigt over tilgængelige klip
    for fil in video_filer:
        event_id = fil.replace('.mp4', '')
        
        # Hent info fra Snowflake
        info = hent_match_data(event_id)
        
        with st.expander(f"🎬 Sekvens: {event_id}" + (f" | Modstander ID: {info[0]}" if info else "")):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.video(os.path.join(video_dir, fil))
            
            with col2:
                if info:
                    st.write(f"**Resultat:** {info[1]} - {info[2]}")
                    st.write(f"**Stadion:** {info[3]}")
                    st.write(f"**Dato:** {info[4]}")
                else:
                    st.warning("Ingen match-data fundet i Snowflake for dette ID.")
                
                st.text_area("Trænernoter:", key=f"note_{event_id}")
                if st.button("Gem analyse", key=f"btn_{event_id}"):
                    st.success("Notat gemt lokalt")
