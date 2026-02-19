import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- 0. DYNAMISK KONFIGURATION ---
try:
    from data.season_show import TEAM_WYID, SEASONNAME
    TEAM_COLOR = '#d31313' 
except ImportError:
    TEAM_WYID = 38331
    SEASONNAME = "2025/2026"
    TEAM_COLOR = '#d31313'

def vis_side(df_shots, df_spillere, hold_map):
    st.markdown("<style>.main .block-container { padding-top: 2rem; }</style>", unsafe_allow_html=True)

    if df_shots is None or df_shots.empty:
        st.warning(f"Ingen skuddata fundet for {SEASONNAME}.")
        return

    # --- 1. SIKKER DATA-RENS ---
    df_s = df_shots.copy()
    df_s.columns = [str(c).upper() for c in df_s.columns]
    
    # Konverter alle vigtige kolonner til numeriske typer for at undgå fejl
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE', 'TEAM_WYID']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce').fillna(0)

    # Hjælpefunktion til booleans (Snowflake sender ofte 1/0 eller True/False)
    def to_bool(val):
        return str(val).lower() in ['true', '1', '1.0', 't', 'y']

    df_s['IS_GOAL'] = df_s['SHOTISGOAL'].apply(to_bool) if 'SHOTISGOAL' in df_s.columns else False

    # Filtrer til eget hold
    df_s = df_s[df_s['TEAM_WYID'] == TEAM_WYID].copy()

    # Formater Modstander-navn
    eget_hold_navn = str(hold_map.get(str(int(TEAM_WYID)), "Hvidovre")).upper()
    
    def clean_label(label):
        if pd.isna(label): return "Ukendt"
        # Fjerner eget holdnavn og overflødige bindestreger
        txt = str(label).upper().replace(eget_hold_navn, "").replace("-", "").strip()
        return f"vs. {txt}" if txt else "Kamp"

    df_s['MODSTANDER'] = df_s['MATCHLABEL'].apply(clean_label) if 'MATCHLABEL' in df_s.columns else "Kamp"

    # Spiller mapping
    s_df = df_spillere.copy()
    s_df.columns = [str(c).upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df.get('NAVN', 'Ukendt')))
    
    df_s['PLAYER_ID_STR'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    df_s['SPILLER_NAVN'] = df_s['PLAYER_ID_STR'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 2. UI LAYOUT ---
    col_map, col_stats = st.columns([2, 1])

    with col_stats:
        # En lille spacer for at flugte med toppen af banen
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=spiller_liste, label_visibility="collapsed")
        
        df_p = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
        df_p = df_p.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_p['NR'] = df_p.index + 1

        # --- BEREGNINGER ---
        SHOTS = len(df_p)
        GOALS = int(df_p['IS_GOAL'].sum())
        XG_TOTAL = df_p['SHOTXG'].sum() if 'SHOTXG' in df_p.columns else 0
        CONV_RATE = (GOALS / SHOTS * 100) if SHOTS > 0 else 0

        # --- METRICS BOKS (Opdateret til dit design) ---
        st.markdown(f"""
            <div style="border-left: 4px solid {TEAM_COLOR}; padding: 20px; background-color: #f1f3f6; border-radius: 0 10px 10px 0; margin-bottom: 10px;">
                <p style="margin:0; color:#666; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Afslutninger / Mål</p>
                <p style="margin:0; font-size:26px; font-weight:800; color:#111;">{SHOTS} / {GOALS}</p>
                
                <div style="margin:15px 0; border-top:1px solid #ddd;"></div>
                
                <p style="margin:0; color:#666; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Konverteringsrate</p>
                <p style="margin:0; font-size:26px; font-weight:800; color:#111;">{CONV_RATE:.1f}%</p>
                
                <div style="margin:15px 0; border-top:1px solid #ddd;"></div>
                
                <p style="margin:0; color:#666; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Total xG</p>
                <p style="margin:0; font-size:26px; font-weight:800; color:#111;">{XG_TOTAL:.2f}</p>
            </div>
        """, unsafe_allow_html=True)

        # --- POPOVER (Hvor tabellen ligger pænt gemt) ---
        with st.popover("Se alle afslutninger", use_container_width=True):
            tabel_df = df_p.copy()
            # Mål-ikon
            tabel_df['RES'] = tabel_df['IS_GOAL'].map({True: "⚽ MÅL", False: "Afslutning"})
            
            # Bodypart mapping
            b_map = {'right_foot': 'Højre', 'left_foot': 'Venstre', 'head': 'Hoved', 'other': 'Andet'}
            tabel_df['DEL'] = tabel_df['SHOTBODYPART'].str.lower().map(b_map).fillna(tabel_df['SHOTBODYPART'])
            
            # xG formatering i tabellen
            if 'SHOTXG' in tabel_df.columns:
                tabel_df['xG'] = tabel_df['SHOTXG'].astype(float).round(2)
            
            # Endelig tabelvisning
            vis_tabel = tabel_df[['NR', 'MODSTANDER', 'MINUTE', 'DEL', 'xG', 'RES']]
            vis_tabel.columns = ['#', 'Kamp', 'Min', 'Del', 'xG', 'Res']
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)

    with col_map:
        # 1. Setup pitch med fast aspect ratio
        pitch = VerticalPitch(
            half=True, 
            pitch_type='wyscout', 
            line_color='#444444', 
            line_zorder=2,
            goal_type='box' # Giver et pænere mål
        )
        
        # Vi definerer en fast figurstørrelse der passer til Streamlit kolonnen
        fig, ax = pitch.draw(figsize=(8, 10)) 
        
        # 2. Zoom - vi justerer lidt på tallene her for at centrere feltet bedre
        # Wyscout feltet stopper ved 100, men vi giver den 2 ekstra for at undgå at klippe målstreget
        ax.set_ylim(48, 102) 

        # 3. Plot skud
        for _, row in df_plot.iterrows():
            is_goal = str(row.get('IS_GOAL', 'false')).lower() in ['true', '1', 't']
            
            # Vi sætter cirklerne lidt ned i størrelse ift. dit screenshot
            # s=500 er ofte for meget i en vertical pitch, vi prøver 300/150
            p_size = 350 if is_goal else 180
            
            # Tegn selve cirklen
            ax.scatter(
                row['LOCATIONY'], 
                row['LOCATIONX'], 
                s=p_size,
                color='gold' if is_goal else TEAM_COLOR, 
                edgecolors='white', 
                linewidth=1.5,
                alpha=1.0, 
                zorder=3
            )
            
            # 4. Tekst-justering
            # Vi gør teksten lidt mindre (fontsize=9), så de ikke "stikker ud" af cirklerne
            ax.text(
                row['LOCATIONY'], 
                row['LOCATIONX'], 
                str(int(row['SHOT_NR'])), 
                color='black' if is_goal else 'white', 
                ha='center', 
                va='center', 
                fontsize=9, 
                fontweight='bold', 
                zorder=4
            )
        
        # Fjern margin omkring plottet for at udnytte pladsen
        st.pyplot(fig, bbox_inches='tight', pad_inches=0)
