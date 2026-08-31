from datetime import datetime, timedelta
from io import StringIO
import time
import base64
import plotly.graph_objects as go
import pandas as pd
import requests
import streamlit as st

from utils.positional_helper import hent_position_for_spiller, beregn_metrics_for_gruppe

# HIF Identitet
HIF_RED = '#df003b'
HIF_BLUE = '#0056a3'

def rens_id(val):
    if pd.isna(val) or str(val).strip() in ["", "nan", "None", "0", "0.0"]: 
        return ""
    # Fjern eventuelle bogstaver (f.eks. 'M') og behold kun cifrene
    clean_val = ''.join(filter(str.isdigit, str(val)))
    if not clean_val:
        # Fallback hvis strengen ikke indeholder cifre, men f.eks. er en ren tekst-id
        clean_val = str(val).strip()
    return clean_val.split('.')[0].strip()

def vis_spiller_billede(img_url, pid):
    pid_c = rens_id(pid)
    url = str(img_url).strip() if pd.notna(img_url) and str(img_url).lower() not in ["0", "0.0", "nan", "none", ""] else ""
    if url == "": return f"https://cdn5.wyscout.com/photos/players/public/{pid_c}.png"
    return url

def vis_side(df_spillere, d1, d2, career_df, d3, advanced_stats_df, primaer_positioner_df=None):
    st.markdown(f"""
        <style>
            .player-card {{
                padding: 20px; border-radius: 12px; border: 1px solid #eee;
                background: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.03);
                margin-bottom: 15px;
            }}
            .card-hif {{ border-left: 10px solid {HIF_RED}; }}
            .card-mod {{ border-right: 10px solid {HIF_BLUE}; text-align: right; }}
            .player-title {{ margin: 0 !important; font-size: 1.6rem; font-weight: 900; line-height: 1.1; }}
            .player-sub {{ margin: 2px 0 12px 0 !important; font-size: 0.95rem; color: gray; text-transform: uppercase; font-weight: 600; }}
            .quick-stats {{ display: flex; gap: 15px; margin-bottom: 15px; border-top: 1px solid #f0f0f0; padding-top: 10px; }}
            .card-mod .quick-stats {{ justify-content: flex-end; }}
            .q-item {{ text-align: center; min-width: 40px; }}
            .q-label {{ font-size: 0.7rem; color: #999; font-weight: bold; text-transform: uppercase; display: block; }}
            .q-val {{ font-size: 1.1rem; font-weight: 800; color: #333; }}
            .stat-row {{ display: flex; justify-content: space-between; padding: 0 5px; border-bottom: 1px solid #f8f8f8; align-items: center; height: 38px; }}
            .stat-label {{ font-size: 0.8rem; color: #777; font-weight: bold; text-transform: uppercase; }}
            .stat-val {{ font-size: 1.1rem; font-weight: 800; }}
            .scouting-header {{ text-align: center; font-weight: 900; font-size: 0.9rem; color: #bbb; text-transform: uppercase; letter-spacing: 3px; margin-top: 35px; margin-bottom: 12px; }}
            .note-box {{ padding: 18px; border-radius: 12px; border: 1px solid #eee; font-size: 1.05rem; line-height: 1.6; background: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.02); margin-bottom: 15px; }}
            .note-hif {{ border-left: 8px solid {HIF_RED}; }}
            .note-mod {{ border-right: 8px solid {HIF_BLUE}; text-align: right; }}
            .center-analysis {{ margin-top: 15px; padding: 15px; background: #fcfcfc; border: 1px solid #eee; border-radius: 10px; }}
        </style>
    """, unsafe_allow_html=True)

    # 1. Indlæs Scouting DB (Grundlaget for sammenligning)
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s.columns = [c.upper().strip() for c in df_s.columns]
        # Omdøb tilbage til display-navne for nemhed
        df_s = df_s.rename(columns={'NAVN': 'Navn', 'DATO': 'Dato', 'STYRKER': 'Styrker', 'UDVIKLING': 'Udvikling', 'VURDERING': 'Vurdering'})
    except:
        st.error("Kunne ikke indlæse scouting_db.csv")
        return

    navne_liste = sorted(df_s['Navn'].unique().tolist())
    if not navne_liste:
        st.info("Ingen spillere fundet i scouting-databasen.")
        return

    c1, c2 = st.columns(2)
    s1_navn = c1.selectbox("Vælg Spiller 1 (Rød)", navne_liste, index=0)
    s2_navn = c2.selectbox("Vælg Spiller 2 (Blå)", navne_liste, index=min(1, len(navne_liste)-1))

    def hent_data(navn):
        # Nyeste rapport
        match = df_s[df_s['Navn'] == navn].sort_values('Dato', ascending=False).iloc[:1]
        if match.empty: return None
        n = match.iloc[0]
        pid = rens_id(n.get('PLAYER_WYID'))

        # --- POSITION: udledt af faktisk kamphistorik (positional_helper) ---
        # Erstatter det tidligere map_position(ROLECODE3), som ofte var tom i WYSCOUT_PLAYERS
        pos_kode, positionsgruppe = "Ukendt", "Ukendt"
        if primaer_positioner_df is not None and not primaer_positioner_df.empty:
            pos_kode, positionsgruppe = hent_position_for_spiller(pid, primaer_positioner_df)

        klub = "Ukendt"

        # A: Tjek lokal trup (df_spillere) for klub (og evt. nødløsning for position)
        if df_spillere is not None and not df_spillere.empty:
            m = df_spillere[df_spillere['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                klub = m.iloc[0].get('TEAMNAME', klub)

        # B: Tjek Snowflake search-liste (d3/sql_players)
        if (klub == "Ukendt") and d3 is not None and not d3.empty:
            m_wy = d3[d3['PLAYER_WYID'].apply(rens_id) == pid]
            if not m_wy.empty:
                klub = m_wy.iloc[0].get('TEAMNAME', klub)

        # Visningstekst for position: brug positionsgruppen, med kode i parentes hvis kendt
        if positionsgruppe != "Ukendt":
            pos_visning = f"{positionsgruppe} ({pos_kode.upper()})" if pos_kode and pos_kode != "Ukendt" else positionsgruppe
        else:
            pos_visning = "Ukendt"

        # C: Billede (fra sql_players/d3)
        img_url = ""
        if d3 is not None and not d3.empty:
            img_m = d3[d3['PLAYER_WYID'].apply(rens_id) == pid]
            if not img_m.empty: img_url = img_m.iloc[0].get('IMAGEDATAURL', '')
        
        # D: Karriere & Kamp Stats (Kampe, Mål, Assists, Minutter)
        stats = {"K": 0, "M": 0, "A": 0, "MIN": 0}
        
        # FØRST: Tjek karriere_df for grundlæggende kamptal
        if career_df is not None and not career_df.empty:
            c_m = career_df[career_df['PLAYER_WYID'].apply(rens_id) == pid]

            def _er_aktiv(val):
                return str(val).strip().upper() in ("TRUE", "1", "T")

            if 'ACTIVE' in c_m.columns:
                curr = c_m[c_m['ACTIVE'].apply(_er_aktiv)]
            else:
                curr = pd.DataFrame()
            target = curr.iloc[0] if not curr.empty else (c_m.iloc[0] if not c_m.empty else None)
            
            if target is not None:
                stats["K"] = int(target.get('MATCHES', 0))
                stats["MIN"] = int(target.get('MINUTES', 0))
                stats["M"] = int(target.get('GOALS', 0))
                stats["A"] = int(target.get('ASSISTS', 0))

        # SECONDARY OVERRIDE: Brug Advanced Stats (df_adv) til Mål og Assists
        # Det er her Andreas Smeds assists gemmer sig!
        if advanced_stats_df is not None and not advanced_stats_df.empty:
            adv_df_upper = advanced_stats_df.copy()
            adv_df_upper.columns = [c.upper() for c in adv_df_upper.columns]
            
            p_adv = adv_df_upper[adv_df_upper['PLAYER_WYID'].apply(rens_id) == pid]
            if not p_adv.empty:
                r_adv = p_adv.iloc[0]
                # Vi opdaterer kun hvis værdien findes (Wyscout bruger ofte GOALS og ASSISTS i adv stats)
                if 'ASSISTS' in r_adv: stats["A"] = int(r_adv['ASSISTS'])
                if 'GOALS' in r_adv: stats["M"] = int(r_adv['GOALS'])
                if 'MINUTESONFIELD' in r_adv: stats["MIN"] = int(r_adv['MINUTESONFIELD'])
        
        lbls = ['TEKNIK', 'AGGRESIVITET', 'BESLUTSOMHED', 'SPILINTELLIGENS', 'FART', 'ATTITUDE', 'LEDEREGENSKABER', 'UDHOLDENHED']

        # --- METRICS: positionsspecifikke i stedet for fast liste (positional_helper) ---
        adv_metrics = beregn_metrics_for_gruppe(pid, positionsgruppe, advanced_stats_df)

        return {
            "navn": navn, "pid": pid, "img": img_url, "pos": pos_visning, "positionsgruppe": positionsgruppe, "klub": klub, "stats": stats,
            "adv": adv_metrics,
            "r": [float(str(n.get(k, 0.1)).replace(',', '.')) for k in lbls],
            "styrker": n.get('Styrker', '-'), "udvikling": n.get('Udvikling', '-'), "vurdering": n.get('Vurdering', '-'),
            "scout_scores": {k: n.get(k, 0) for k in lbls}
        }

    p1 = hent_data(s1_navn)
    p2 = hent_data(s2_navn)
    if not p1 or not p2: return

    # --- RENDER LAYOUT ---
    col_left, col_center, col_right = st.columns([4.2, 3.6, 4.2])

    # SPILLER 1 (VENSTRE)
    with col_left:
        st.markdown(f"""<div class='player-card card-hif'>
            <div style='display: flex; gap: 15px; align-items: start;'>
                <img src='{vis_spiller_billede(p1["img"], p1["pid"])}' style='width: 90px; border-radius: 8px;'>
                <div style='flex-grow: 1;'>
                    <p class='player-title' style='color:{HIF_RED};'>{p1['navn']}</p>
                    <p class='player-sub'>{p1['pos']} | {p1['klub']}</p>
                    <div class='quick-stats'>
                        <div class='q-item'><span class='q-label'>K</span><span class='q-val'>{p1['stats']['K']}</span></div>
                        <div class='q-item'><span class='q-label'>M</span><span class='q-val'>{p1['stats']['M']}</span></div>
                        <div class='q-item'><span class='q-label'>A</span><span class='q-val'>{p1['stats']['A']}</span></div>
                        <div class='q-item'><span class='q-label'>MIN</span><span class='q-val'>{p1['stats']['MIN']}</span></div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        if p1['adv']:
            for k, v in p1['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-label'>{k}</span><span class='stat-val' style='color:{HIF_RED}'>{v}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # RADAR (MIDTEN)
    with col_center:
        labels = ['Teknik', 'Aggressiv', 'Beslut.', 'Intelligens', 'Fart', 'Attitude', 'Leder', 'Udhold.']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_RED, name=p1['navn'], opacity=0.4))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_BLUE, name=p2['navn'], opacity=0.4))
        
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=False, range=[0, 6])),
            height=350, margin=dict(l=40, r=40, t=20, b=20), showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # SPILLER 2 (HØJRE)
    with col_right:
        st.markdown(f"""<div class='player-card card-mod'>
            <div style='display: flex; gap: 15px; align-items: start; flex-direction: row-reverse;'>
                <img src='{vis_spiller_billede(p2["img"], p2["pid"])}' style='width: 90px; border-radius: 8px;'>
                <div style='flex-grow: 1;'>
                    <p class='player-title' style='color:{HIF_BLUE};'>{p2['navn']}</p>
                    <p class='player-sub'>{p2['pos']} | {p2['klub']}</p>
                    <div class='quick-stats'>
                        <div class='q-item'><span class='q-label'>MIN</span><span class='q-val'>{p2['stats']['MIN']}</span></div>
                        <div class='q-item'><span class='q-label'>A</span><span class='q-val'>{p2['stats']['A']}</span></div>
                        <div class='q-item'><span class='q-label'>M</span><span class='q-val'>{p2['stats']['M']}</span></div>
                        <div class='q-item'><span class='q-label'>K</span><span class='q-val'>{p2['stats']['K']}</span></div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        if p2['adv']:
            for k, v in p2['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-val' style='color:{HIF_BLUE}'>{v}</span><span class='stat-label'>{k}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- SCOUTING NOTER ---
    st.markdown("<hr style='margin: 20px 0 10px 0; border: 0; border-top: 2px solid #eee;'>", unsafe_allow_html=True)
    
    def scouting_row(label, text1, text2):
        st.markdown(f"<div class='scouting-header'>{label}</div>", unsafe_allow_html=True)
        sc1, sc2 = st.columns(2)
        sc1.markdown(f"<div class='note-box note-hif'>{text1}</div>", unsafe_allow_html=True)
        sc2.markdown(f"<div class='note-box note-mod'>{text2}</div>", unsafe_allow_html=True)

    scouting_row("Styrker", p1["styrker"], p2["styrker"])
    scouting_row("Udviklingspotentiale", p1["udvikling"], p2["udvikling"])
    scouting_row("Scout Vurdering", f"<b>{p1['vurdering']}</b>", f"<b>{p2['vurdering']}</b>")
