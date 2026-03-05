import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        v = float(str(val).replace(',', '.'))
        return int(v) if v <= 6 else 6
    except: return 0

@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, career_df):
    clean_p_id = rens_id(p_data.get('PLAYER_WYID', ''))
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].copy()
    nyeste = historik.sort_values('DATO', ascending=True).iloc[-1] if not historik.empty else p_data
    
    h1, h2 = st.columns([1, 4])
    with h1:
        st.image(p_data.get('VIS_BILLEDE', ""), width=115)
    with h2:
        st.markdown(f"## {nyeste.get('NAVN', 'Ukendt')}")
        st.caption(f"{nyeste.get('KLUB', 'Ingen klub')} | Snit: {nyeste.get('RATING_AVG', 0)}")

    t1, t2, t3, t4, t5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radar"])
    
    with t1:
        # Metrikker... (Samme som før)
        m_cols = st.columns(4)
        metrics = [("Teknik", "TEKNIK"), ("Fart", "FART"), ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
                   ("Udholdenhed", "UDHOLDENHED"), ("Leder", "LEDEREGENSKABER"), ("Beslutning", "BESLUTSOMHED"), ("Intelligens", "SPILINTELLIGENS")]
        for i, (label, col) in enumerate(metrics):
            m_cols[i % 4].metric(label, rens_metrik_vaerdi(nyeste.get(col, 0)))

    with t4:
        st.subheader("Karriere Stats")
        if career_df is not None and not career_df.empty:
            # Matcher præcis på ID
            df_p = career_df[career_df['PLAYER_WYID'] == clean_p_id].copy()
            
            if not df_p.empty:
                # Kolonnerne du bad om (De er nu i UPPER pga. Snowflake)
                target_cols = ['SEASONNAME', 'TEAMNAME', 'MATCHES', 'MINUTES', 'GOALS', 'ASSISTS', 'YELLOWCARD', 'REDCARDS']
                
                # Mapping til pæne danske navne
                pretty_map = {
                    'SEASONNAME': 'Sæson', 'TEAMNAME': 'Klub', 'MATCHES': 'Kampe', 
                    'MINUTES': 'Min', 'GOALS': 'Mål', 'ASSISTS': 'Ass', 
                    'YELLOWCARD': 'Gule', 'REDCARDS': 'Røde'
                }
                
                # Filtrer og omdøb
                final_df = df_p[[c for c in target_cols if c in df_p.columns]].rename(columns=pretty_map)
                st.dataframe(final_df, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Ingen stats fundet i Snowflake for ID: {clean_p_id}")
        else:
            st.error("Stats-databasen er tom. Tjek Snowflake-forbindelsen.")

    with t5:
        # Radar Chart... (Lukket cirkel)
        categories = ['Beslutning', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Leder', 'Teknik', 'Intelligens']
        keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in keys]
        fig = go.Figure(go.Scatterpolar(r=v + [v[0]], theta=categories + [categories[0]], fill='toself', fillcolor='rgba(223, 0, 59, 0.3)', line=dict(color='#df003b')))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

# ... (Resten af vis_side er uændret)
