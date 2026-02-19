import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- 0. DYNAMISK KONFIGURATION ---
try:
    from data.season_show import TEAM_WYID, SEASONNAME
    # Standard HIF farve
    TEAM_COLOR = '#d31313' 
except ImportError:
    TEAM_WYID = 38331
    SEASONNAME = "2025/2026"
    TEAM_COLOR = '#d31313'

def vis_side(df_shots, df_spillere, hold_map):
    """
    Viser skudkort baseret på Snowflake data med optimeret layout og metrics.
    """
    # Juster top-padding for at flugte med menuen
    st.markdown("<style>.main .block-container { padding-top: 1.5rem; }</style>", unsafe_allow_html=True)

    if df_shots is None or df_shots.empty:
        st.warning(f"Ingen skuddata fundet i Snowflake for {SEASONNAME}.")
        return

    # --- 1. DATA-RENS & FORMATEING ---
    df_s = df_shots.copy()
    df_s.columns = [str(c).upper() for c in df_s.columns]
    
    # Numerisk konvertering for at sikre stabilitet
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE', 'TEAM_WYID']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce').fillna(0)

    # Håndtering af boolske værdier fra Snowflake (1/0 eller True/False)
    def to_bool(val):
        return str(val).lower() in ['true', '1', '1.0', 't', 'y']

    df_s['IS_GOAL'] = df_s['SHOTISGOAL'].apply(to_bool) if 'SHOTISGOAL' in df_s.columns else False
    
    # Filtrer til eget hold
    df_s = df_s[df_s['TEAM_WYID'] == TEAM_WYID].copy()

    # Formater Modstander-navn (fjerner eget holdnavn fra MATCHLABEL)
    eget_hold_navn = str(hold_map.get(str(int(TEAM_WYID)), "Hvidovre")).upper()
    
    def clean_label(label):
        if pd.isna(label): return "Ukendt"
        txt = str(label).upper().replace(eget_hold_navn, "").replace("-", "").strip()
        return f"vs. {txt.title()}" if txt else "Kamp"

    df_s['MODSTANDER'] = df_s['MATCHLABEL'].apply(clean_label) if 'MATCHLABEL' in df_s.columns else "Kamp"

    # Spiller mapping (kobler ID til navn fra players.csv)
    s_df = df_spillere.copy()
    s_df.columns = [str(c).upper() for c in s_df.columns]
    s_df['PLAYER_WYID_STR'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID_STR'], s_df.get('NAVN', 'Ukendt')))
    
    df_s['PLAYER_ID_STR'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    df_s['SPILLER_NAVN'] = df_s['PLAYER_ID_STR'].map(navne_dict).fillna("Ukendt Spiller")

    if df_s.empty:
        st.info(f"Ingen skud registreret for det valgte hold i denne batch.")
        return

    # --- 2. UI LAYOUT ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        # Spiller-vælger
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=spiller_liste, label_visibility="collapsed")
        
        df_p = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
        df_p = df_p.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_p['NR'] = df_p.index + 1

        # Beregninger til metrics
        SHOTS = len(df_p)
        GOALS = int(df_p['IS_GOAL'].sum())
        XG_TOTAL = df_p['SHOTXG'].sum()
        CONV_RATE = (GOALS / SHOTS * 100) if SHOTS > 0 else 0

        # Metrics boks (Designet efter dit screenshot)
        st.markdown(f"""
            <div style="border-left: 5px solid {TEAM_COLOR}; padding: 15px 20px; background-color: #f1f3f6; border-radius: 0 8px 8px 0; margin-top: 10px;">
                <p style="margin:0; color:#555; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Afslutninger / Mål</p>
                <p style="margin:0 0 12px 0; font-size:28px; font-weight:800; color:#111;">{SHOTS} / {GOALS}</p>
                
                <div style="border-top:1px solid #d1d5db; margin-bottom:12px;"></div>
                
                <p style="margin:0; color:#555; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Konverteringsrate</p>
                <p style="margin:0 0 12px 0; font-size:28px; font-weight:800; color:#111;">{CONV_RATE:.1f}%</p>
                
                <div style="border-top:1px solid #d1d5db; margin-bottom:12px;"></div>
                
                <p style="margin:0; color:#555; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Total xG</p>
                <p style="margin:0; font-size:28px; font-weight:800; color:#111;">{XG_TOTAL:.2f}</p>
            </div>
        """, unsafe_allow_html=True)

        # Popover med detaljeret tabel
        with st.popover("Se alle afslutninger", use_container_width=True):
            tabel_df = df_p.copy()
            tabel_df['RES'] = tabel_df['IS_GOAL'].map({True: "⚽ MÅL", False: "Afslutning"})
            
            # Dansk mapping af kropsdele
            b_map = {'right_foot': 'Højre', 'left_foot': 'Venstre', 'head': 'Hoved', 'other': 'Andet'}
            tabel_df['DEL'] = tabel_df['SHOTBODYPART'].str.lower().map(b_map).fillna(tabel_df['SHOTBODYPART'])
            
            vis_tabel = tabel_df[['NR', 'MODSTANDER', 'MINUTE', 'DEL', 'SHOTXG', 'RES']]
            vis_tabel.columns = ['#', 'Kamp', 'Min', 'Del', 'xG', 'Res']
            
            # Formater xG til 2 decimaler i tabellen
            st.dataframe(
                vis_tabel.style.format({'xG': '{:.2f}'}), 
                hide_index=True, 
                use_container_width=True
            )

    with col_map:
        # Opsætning af banen
        pitch = VerticalPitch(
            half=True, 
            pitch_type='wyscout', 
            line_color='#444444', 
            line_zorder=2,
            goal_type='box'
        )
        fig, ax = pitch.draw(figsize=(8, 10))
        
        # Zoom ind på modstanderens halvdel (Wyscout koordinater)
        ax.set_ylim(48, 102) 

        # Plot hver afslutning
        for _, row in df_p.iterrows():
            is_goal = row['IS_GOAL']
            
            # Punktstørrelse justeret for at undgå for meget overlap
            p_size = 280 if is_goal else 140 
            
            ax.scatter(
                row['LOCATIONY'], 
                row['LOCATIONX'], 
                s=p_size,
                color='gold' if is_goal else TEAM_COLOR, 
                edgecolors='white', 
                linewidth=1.2, 
                alpha=1.0, 
                zorder=3
            )
            
            # Skriv nummeret på skuddet i cirklen
            ax.text(
                row['LOCATIONY'], 
                row['LOCATIONX'], 
                str(int(row['NR'])), 
                color='black' if is_goal else 'white', 
                ha='center', 
                va='center', 
                fontsize=8 if not is_goal else 9, 
                fontweight='bold', 
                zorder=4
            )
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0)
