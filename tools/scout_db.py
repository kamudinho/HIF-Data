import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. HJÆLPEFUNKTIONER ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def map_position(row):
    # Prøver først kolonnen fra players.csv, dernæst fra scouting_db.csv
    csv_pos = str(row.get('POS', row.get('POSITION', 'Ukendt'))).strip().split('.')[0]
    pos_dict = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    # Hvis det er en kode (1-11), map den. Ellers brug teksten direkte (f.eks. "Stopper")
    return pos_dict.get(csv_pos, csv_pos)

def vis_spiller_billede(pid, w=110):
    pid_clean = str(pid).split('.')[0].strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except: st.image(std, width=w)

# --- 2. LAYOUT FUNKTIONER ---
def vis_metrikker(row):
    m_cols = st.columns(4)
    metrics = [
        ("Teknik", "TEKNIK"), ("Fart", "FART"), 
        ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
        ("Udholdenhed", "UDHOLDENHED"), ("Leder", "LEDEREGENSKABER"), 
        ("Beslutning", "BESLUTSOMHED"), ("Intelligens", "SPILINTELLIGENS")
    ]
    for i, (label, col) in enumerate(metrics):
        val = rens_metrik_vaerdi(row.get(col, 0))
        m_cols[i % 4].metric(label, f"{val}")

# --- 3. PROFIL DIALOG ---
@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, s_df, fs_df):
    clean_p_id = str(p_data['PLAYER_WYID'])
    # Hent alle historiske rapporter for denne spiller
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].sort_values('DATO_DT', ascending=True)
    nyeste = historik.iloc[-1]
    
    head_col1, head_col2 = st.columns([1, 4])
    with head_col1: vis_spiller_billede(clean_p_id, w=115)
    with head_col2:
        st.markdown(f"## {nyeste.get('NAVN', 'Ukendt')}")
        st.markdown(f"**{nyeste.get('KLUB', '')}** | {nyeste.get('POSITION_VISNING', '')} | Snit: {nyeste.get('RATING_AVG', 0)}")

    t1, t2, t3, t4, t5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radar"])
    
    with t1:
        vis_metrikker(nyeste)
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
        with c2: st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")
        with c3: st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', '-')}")

    with t2:
        for _, row in historik.iloc[::-1].iterrows():
            with st.expander(f"Dato: {row.get('DATO')} | Scout: {row.get('SCOUT')} | Rating: {row.get('RATING_AVG')}"):
                vis_metrikker(row)

    with t3:
        # Udviklingskurve baseret på historik-rækkerne i scouting_db.csv
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=historik['DATO_DT'], y=historik['RATING_AVG'], mode='markers+lines', line=dict(color='#df003b')))
        fig_line.update_layout(height=300, yaxis=dict(range=[0.8, 6.2]), plot_bgcolor='white')
        st.plotly_chart(fig_line, use_container_width=True)

    with t4:
        # Snowflake stats
        df_stats = s_df[s_df['PLAYER_WYID'] == clean_p_id].copy()
        if not df_stats.empty:
            st.dataframe(df_stats[['SEASONNAME', 'TEAMNAME', 'MATCHES', 'GOALS', 'XG', 'ASSISTS']], use_container_width=True, hide_index=True)
        else: st.info("Ingen Snowflake data fundet for denne spiller.")

    with t5:
        # Radar baseret på de subjektive scout-tal
        categories = ['Teknik', 'Intelligens', 'Beslutning', 'Leder', 'Udholdenhed', 'Fart', 'Aggresivitet', 'Attitude']
        cols = ['TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'LEDEREGENSKABER', 'UDHOLDENHED', 'FART', 'AGGRESIVITET', 'ATTITUDE']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in cols]
        fig_radar = go.Figure(go.Scatterpolar(r=v + [v[0]], theta=categories + [categories[0]], fill='toself', line=dict(color='#df003b')))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False)
        st.plotly_chart(fig_radar, use_container_width=True)

# --- 4. HOVEDFUNKTION ---
def vis_side(scout_df, spillere_df, stats_df):
    # Standardisering
    for d in [scout_df, spillere_df, stats_df]:
        if d is not None and not d.empty:
            d.columns = [c.upper() for c in d.columns]
    
    # ID Rensning
    def clean(df):
        if df is not None and 'PLAYER_WYID' in df.columns:
            df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        return df

    scout_df = clean(scout_df)
    spillere_df = clean(spillere_df)
    stats_df = clean(stats_df)

    # Merge og Position
    df = scout_df.copy()
    if 'PLAYER_WYID' in spillere_df.columns:
        df = df.merge(spillere_df[['PLAYER_WYID', 'POS', 'ROLECODE3']].drop_duplicates('PLAYER_WYID'), on='PLAYER_WYID', how='left')
    
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    
    st.subheader("Scouting Database")
    
    # Find den nyeste rapport pr. spiller til oversigten
    f_df = df.sort_values('DATO_DT').groupby('PLAYER_WYID').tail(1).copy()
    
    search = st.text_input("Søg...", placeholder="Navn eller klub...", label_visibility="collapsed")
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]
    
    disp = f_df[['NAVN', 'POSITION_VISNING', 'KLUB', 'RATING_AVG', 'STATUS', 'DATO', 'SCOUT']].copy()
    event = st.dataframe(disp, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

    if len(event.selection.rows) > 0:
        p_row = f_df.iloc[event.selection.rows[0]]
        vis_profil(p_row, df, stats_df, pd.DataFrame())
