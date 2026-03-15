import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

OPTA_MAP_DK = {
    1: "Aflevering", 2: "Aflevering", 3: "Dribling", 4: "Tackling", 
    5: "Frispark", 6: "Hjørnespark", 7: "Tackling", 8: "Interception",
    10: "Redning", 12: "Skud", 13: "Skud", 14: "Skud", 15: "Skud", 
    16: "MÅL", 43: "Frispark", 44: "Indkast", 49: "Opsamling", 50: "Opsnapning",
    107: "Restart"
}

def vis_side(dp):
    # CSS: Strammer padding op og fjerner margin i toppen
    st.markdown(f"""
        <style>
            .block-container {{ padding-top: 1rem; }}
            .stat-box-side {{ 
                background-color: #f8f9fa; 
                padding: 8px 12px; 
                border-radius: 5px; 
                border-left: 5px solid {HIF_RED}; 
                margin-bottom: 6px; 
            }}
            .dot {{ height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }}
            .play-flow-container {{ 
                background: #ffffff; 
                padding: 12px; 
                border-radius: 8px; 
                border: 1px solid #eee; 
                margin-top: 5px; 
                line-height: 1.6;
            }}
            .flow-step {{ font-weight: 700; color: #333; font-size: 0.9rem; }}
            .flow-action {{ color: #666; font-size: 0.8rem; font-weight: 400; }}
            .flow-arrow {{ color: {HIF_RED}; margin: 0 6px; font-weight: bold; }}
            /* Fjerner Streamlits standard-afstand over tabeller */
            .stTable {{ margin-top: -15px; }}
        </style>
    """, unsafe_allow_html=True)

    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df_raw.empty: return

    df = df_raw.copy()
    df.columns = [c.upper() for c in df.columns]

    col_x = 'RAW_X' if 'RAW_X' in df.columns else ('EVENT_X' if 'EVENT_X' in df.columns else None)
    col_y = 'RAW_Y' if 'RAW_Y' in df.columns else ('EVENT_Y' if 'EVENT_Y' in df.columns else None)
    if not col_x: return

    df['EVENT_CONTESTANT_OPTAUUID'] = df['EVENT_CONTESTANT_OPTAUUID'].astype(str).str.lower()
    local_hif_uuid = HIF_UUID.lower()
    
    goals = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goals.empty: return
    goals['LABEL'] = goals.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        # Flyt selectbox op så den flugter med banen
        sel_label = st.selectbox("Vælg mål", options=goals['LABEL'].unique(), label_visibility="collapsed")
        sel_row = goals[goals['LABEL'] == sel_label].iloc[0]
        
        hif_seq = df[(df['SEQUENCEID'] == sel_row['SEQUENCEID']) & (df['EVENT_CONTESTANT_OPTAUUID'] == local_hif_uuid)].copy()
        hif_seq = hif_seq.sort_values('EVENT_TIMESTAMP').reset_index(drop=True)

        if not hif_seq.empty:
            scorer = hif_seq.iloc[-1]['PLAYER_NAME'].split()[-1] if pd.notnull(hif_seq.iloc[-1]['PLAYER_NAME']) else "HIF"
            assist = hif_seq.iloc[-2]['PLAYER_NAME'].split()[-1] if len(hif_seq) > 1 else "Solo"
            
            st.markdown(f'<div class="stat-box-side"><span class="dot" style="background-color:{HIF_RED}"></span><b>Målscorer:</b> {scorer}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box-side" style="border-left-color:{ASSIST_BLUE}"><span class="dot" style="background-color:{ASSIST_BLUE}"></span><b>Assist:</b> {assist}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Involveringer i sekvens")
        
        all_hif_game = df[df['EVENT_CONTESTANT_OPTAUUID'] == local_hif_uuid].copy()
        if not all_hif_game.empty:
            all_hif_game['Spiller'] = all_hif_game['PLAYER_NAME'].apply(lambda x: x.split()[-1] if pd.notnull(x) else "HIF")
            top_players = all_hif_game['Spiller'].value_counts().reset_index()
            top_players.columns = ['Spiller', 'Aktioner']
            st.table(top_players.head(10))

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        # Justeret figsize og constrained_layout for at mindske whitespace
        fig, ax = pitch.draw(figsize=(9, 6))
        fig.set_facecolor('none') # Gør figuren gennemsigtig så den blender ind
        
        flip = True if sel_row[col_x] < 50 else False
        
        prev = None
        for i, r in hif_seq.iterrows():
            cx, cy = (100 - r[col_x] if flip else r[col_x]), (100 - r[col_y] if flip else r[col_y])
            if prev:
                ax.annotate('', xy=(cx, cy), xytext=(prev[0], prev[1]),
                            arrowprops=dict(arrowstyle='->', color='#ccc', lw=1.5, alpha=0.4, shrinkA=5, shrinkB=5))
            
            p_name = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else ""
            dot_col = HIF_RED if r['EVENT_TYPEID'] == 16 else (ASSIST_BLUE if p_name == assist else '#aaaaaa')
            pitch.scatter(cx, cy, s=180, color=dot_col, edgecolors='white', ax=ax, zorder=5)
            ax.text(cx, cy + 2.5, p_name, fontsize=8, ha='center', fontweight='bold')
            prev = (cx, cy)
        
        # Bruger bbox_inches='tight' for at fjerne hvid margin omkring plottet
        st.pyplot(fig, bbox_inches='tight', pad_inches=0)

        # Sekvens-tekst lige under banen
        steps = []
        for _, r in hif_seq.iterrows():
            p = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "HIF"
            tid = int(r['EVENT_TYPEID'])
            h = OPTA_MAP_DK.get(tid, f"Aktion {tid}")
            if tid == 16: h = "MÅL"
            steps.append(f'<span class="flow-step">{p}</span> <span class="flow-action">({h})</span>')
        
        flow_string = ' <span class="flow-arrow">→</span> '.join(steps)
        st.markdown(f'<div class="play-flow-container">{flow_string}</div>', unsafe_allow_html=True)
