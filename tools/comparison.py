import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.season_show import SEASONNAME

# --- 1. HJÆLPEFUNKTIONER ---
def map_position(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant",
        "GKP": "Målmand", "DEF": "Forsvar", "MID": "Midtbane", "FWD": "Angreb"
    }
    s_code = str(pos_code).split('.')[0].upper()
    return pos_map.get(s_code, "Ukendt")

def vis_spiller_billede(img_url, w=110):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    if pd.isna(img_url) or str(img_url).strip() in ["", "nan", "None"]:
        st.image(std, width=w)
    else:
        st.image(img_url, width=w)

def hent_spiller_stats(pid, career_df):
    """Henter karriere-stats fra Snowflake (dp['career'])"""
    if career_df is None or career_df.empty:
        return pd.Series()
    
    pid_s = str(pid).split('.')[0].strip()
    # Vi kigger efter den aktive sæson i din karriere-data
    match = career_df[
        (career_df['PLAYER_WYID'].astype(str) == pid_s) & 
        (career_df['SEASONNAME'].astype(str).str.contains(SEASONNAME))
    ]
    
    if not match.empty:
        return match.iloc[0]
    
    # Fallback: Tag nyeste hvis sæsonen ikke findes
    backup = career_df[career_df['PLAYER_WYID'].astype(str) == pid_s]
    return backup.iloc[0] if not backup.empty else pd.Series()

# --- 2. HOVEDFUNKTION ---
def vis_side(df_spillere, playerstats, df_scout, career_df, season_filter):
    # Standardiser kolonnenavne for at undgå fejl
    if df_spillere is not None: df_spillere.columns = [c.upper() for c in df_spillere.columns]
    if df_scout is not None: df_scout.columns = [c.upper() for c in df_scout.columns]
    if career_df is not None: career_df.columns = [c.upper() for c in career_df.columns]

    # 1. Byg navne-lookup (Kombinerer truppen og gemte scouting-rapporter)
    df_p = df_spillere.copy() if df_spillere is not None else pd.DataFrame()
    if not df_p.empty and 'NAVN' not in df_p.columns:
        df_p['NAVN'] = (df_p.get('FIRSTNAME', '').fillna('') + " " + df_p.get('LASTNAME', '').fillna('')).str.strip()
    
    df_s = df_scout.copy() if df_scout is not None else pd.DataFrame()
    
    # Saml alle unikke spillere vi kender
    lookup_list = []
    if not df_p.empty: lookup_list.append(df_p[['NAVN', 'PLAYER_WYID']])
    if not df_s.empty: lookup_list.append(df_s[['NAVN', 'PLAYER_WYID']])
    
    if not lookup_list:
        st.warning("Ingen spillere fundet i systemet.")
        return
        
    combined_lookup = pd.concat(lookup_list).drop_duplicates(subset=['PLAYER_WYID'])
    navne_liste = sorted(combined_lookup['NAVN'].unique())

    # --- UI VALG ---
    st.markdown(f'<div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:10px;"><h3 style="color:white; margin:0; text-align:center;">SCOUTING: SAMMENLIGNING</h3></div>', unsafe_allow_html=True)
    
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1))

    def hent_alle_info(navn):
        match = combined_lookup[combined_lookup['NAVN'] == navn]
        if match.empty: return None
        pid = str(match.iloc[0]['PLAYER_WYID']).split('.')[0]

        # Find stamdata (Klub, Position, Billede)
        img_url, klub, pos = None, "Ukendt", "Ukendt"
        
        # Tjek først i truppen (df_p)
        p_match = df_p[df_p['PLAYER_WYID'].astype(str) == pid]
        if not p_match.empty:
            img_url = p_match.iloc[0].get('IMAGEDATAURL')
            klub = p_match.iloc[0].get('TEAMNAME', 'Hvidovre IF')
            pos = map_position(p_match.iloc[0].get('ROLECODE3', ''))
        else:
            # Ellers tjek i scouting historik (df_s)
            s_match = df_s[df_s['PLAYER_WYID'].astype(str) == pid]
            if not s_match.empty:
                klub = s_match.iloc[-1].get('KLUB', 'Scouting')
                pos = s_match.iloc[-1].get('POSITION', 'Ukendt')

        # Hent stats fra karriere-data (Snowflake)
        s_data = hent_spiller_stats(pid, career_df)
        stats = {
            'KAMPE': int(s_data.get('APPEARANCES', 0)),
            'MIN': int(s_data.get('MINUTESPLAYED', 0)),
            'MÅL': int(s_data.get('GOAL', 0))
        }

        # Hent tekniske ratings fra scouting CSV
        tech = {k: 0.0 for k in ['FART', 'UDHOLDENHED', 'TEKNIK', 'SPILINTELLIGENS', 'BESLUTSOMHED', 'ATTITUDE', 'LEDEREGENSKABER', 'AGGRESIVITET']}
        if not df_s.empty:
            n = df_s[df_s['PLAYER_WYID'].astype(str) == pid]
            if not n.empty:
                n = n.iloc[-1]
                # Map dine CSV navne til radar-navne
                tech['FART'] = n.get('FART', 0)
                tech['UDHOLDENHED'] = n.get('UDHOLDENHED', 0)
                tech['TEKNIK'] = n.get('TEKNIK', 0)
                tech['SPILINTELLIGENS'] = n.get('SPILINTELLIGENS', 0)
                tech['BESLUTSOMHED'] = n.get('BESLUTSOMHED', 0)
                tech['ATTITUDE'] = n.get('ATTITUDE', 0)
                tech['LEDEREGENSKABER'] = n.get('LEDEREGENSKABER', 0)
                tech['AGGRESIVITET'] = n.get('AGGRESIVITET', 0)
        
        return pid, klub, pos, stats, tech, img_url, navn

    res1 = hent_alle_info(s1_navn)
    res2 = hent_alle_info(s2_navn)

    # --- VISNING ---
    col1, col2, col3 = st.columns([3, 4, 3])
    
    def vis_profil_kort(res, side, color):
        if not res: return
        pid, klub, pos, stats, tech, img_url, navn = res
        align = "left" if side == "venstre" else "right"
        st.markdown(f"<div style='text-align:{align};'><h3 style='color:{color}; margin-bottom:0;'>{navn}</h3><p style='color:gray; margin-top:0;'>{pos} | {klub}</p></div>", unsafe_allow_html=True)
        
        c_img, c_mtr = (st.columns([1, 1]) if side == "venstre" else st.columns([1, 1]))
        with (c_img if side == "venstre" else c_mtr):
            vis_spiller_billede(img_url)
        with (c_mtr if side == "venstre" else c_img):
            st.metric("Mål", stats['MÅL'])
            st.metric("Kampe", stats['KAMPE'])

    with col1: vis_profil_kort(res1, "venstre", "#df003b")
    with col3: vis_profil_kort(res2, "højre", "#0056a3")

    with col2:
        if res1 and res2:
            # Radar Chart
            categories = ['Fart', 'Udholdenhed', 'Teknik', 'Spil-int.', 'Beslut.', 'Attitude', 'Leder', 'Aggres.']
            def get_radar_vals(t):
                v = [t['FART'], t['UDHOLDENHED'], t['TEKNIK'], t['SPILINTELLIGENS'], t['BESLUTSOMHED'], t['ATTITUDE'], t['LEDEREGENSKABER'], t['AGGRESIVITET']]
                v.append(v[0]) # Luk cirklen
                return v
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=get_radar_vals(res1[4]), theta=categories+[categories[0]], fill='toself', name=s1_navn, line_color='#df003b'))
            fig.add_trace(go.Scatterpolar(r=get_radar_vals(res2[4]), theta=categories+[categories[0]], fill='toself', name=s2_navn, line_color='#0056a3'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), height=350, margin=dict(l=40, r=40, t=20, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # --- TABS MED STATS ---
    st.divider()
    tab1, tab2 = st.tabs(["Karriere Stats", "Scouting Noter"])
    
    with tab1:
        if res1 and res2:
            s1_stats = hent_spiller_stats(res1[0], career_df)
            s2_stats = hent_spiller_stats(res2[0], career_df)
            
            c1, c2, c3 = st.columns([2,1,2])
            # Enkel række eksempel
            def stat_row(label, v1, v2):
                c1.markdown(f"<div style='text-align:right;'>{v1}</div>", unsafe_allow_html=True)
                c2.markdown(f"<div style='text-align:center; color:gray;'>{label}</div>", unsafe_allow_html=True)
                c3.markdown(f"<div style='text-align:left;'>{v2}</div>", unsafe_allow_html=True)
            
            stat_row("Sæson", s1_stats.get('SEASONNAME', '-'), s2_stats.get('SEASONNAME', '-'))
            stat_row("Kampe", s1_stats.get('APPEARANCES', 0), s2_stats.get('APPEARANCES', 0))
            stat_row("Minutter", s1_stats.get('MINUTESPLAYED', 0), s2_stats.get('MINUTESPLAYED', 0))
            stat_row("Mål", s1_stats.get('GOAL', 0), s2_stats.get('GOAL', 0))

    with tab2:
        c1, c2 = st.columns(2)
        if res1 and not df_s.empty:
            note1 = df_s[df_s['PLAYER_WYID'].astype(str) == res1[0]]
            if not note1.empty: c1.info(f"**Vurdering {res1[6]}:**\n\n{note1.iloc[-1].get('VURDERING', 'Ingen note')}")
        if res2 and not df_s.empty:
            note2 = df_s[df_s['PLAYER_WYID'].astype(str) == res2[0]]
            if not note2.empty: c2.info(f"**Vurdering {res2[6]}:**\n\n{note2.iloc[-1].get('VURDERING', 'Ingen note')}")
