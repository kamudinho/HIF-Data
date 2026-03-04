import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
HIF_BLUE = '#0056a3'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp):
    # Styling af bokse
    st.markdown("""
        <style>
        .stat-container { display: flex; gap: 10px; margin-bottom: 20px; }
        .stat-box { 
            padding: 15px; border-radius: 8px; background: #f0f2f6; 
            border-left: 5px solid #cc0000; flex: 1; text-align: center;
        }
        .stat-label { font-size: 12px; text-transform: uppercase; color: #555; font-weight: bold; }
        .stat-value { font-size: 24px; font-weight: bold; color: #111; }
        </style>
    """, unsafe_allow_html=True)

    df_raw = dp.get('opta_shotevents', pd.DataFrame())
    
    if df_raw.empty:
        st.warning("Data hentet, men tabellen er tom. Tjek database-forbindelsen.")
        return

    # Filter til HIF og konvertering af koordinater
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_END_X', 'PASS_END_Y']:
        df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)
    
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    with tab1:
        # Skud (13,14,15,16)
        df_skud = df_hif[df_hif['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        
        st.markdown(f"""
            <div class="stat-container">
                <div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(df_skud)}</div></div>
                <div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(df_skud[df_skud.EVENT_TYPEID == 16])}</div></div>
            </div>
        """, unsafe_allow_html=True)

        pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        if not df_skud.empty:
            # Mål
            pitch.scatter(df_skud[df_skud.EVENT_TYPEID == 16].EVENT_X, df_skud[df_skud.EVENT_TYPEID == 16].EVENT_Y, 
                         s=200, c=HIF_RED, edgecolors='black', label='Mål', ax=ax, zorder=3)
            # Missede
            pitch.scatter(df_skud[df_skud.EVENT_TYPEID != 16].EVENT_X, df_skud[df_skud.EVENT_TYPEID != 16].EVENT_Y, 
                         s=150, c='white', edgecolors=HIF_RED, label='Andet skud', ax=ax, zorder=2)
            ax.legend(loc='lower center', bbox_to_anchor=(0.5, 0.02), ncol=2)
        st.pyplot(fig)

    with tab2:
        # Chancer (Type 1 + Qual 210/29)
        df_chance = df_hif[(df_hif['EVENT_TYPEID'] == 1) & (df_hif['QUAL_STR'].str.contains('210|29'))].copy()
        
        st.markdown(f"""
            <div class="stat-container">
                <div class="stat-box" style="border-left-color: {HIF_GOLD}"><div class="stat-label">Assists</div><div class="stat-value">{df_chance.QUAL_STR.str.contains('210').sum()}</div></div>
                <div class="stat-box" style="border-left-color: {HIF_BLUE}"><div class="stat-label">Key Passes</div><div class="stat-value">{df_chance.QUAL_STR.str.contains('29').sum()}</div></div>
            </div>
        """, unsafe_allow_html=True)

        pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
        
        if not df_chance.empty:
            pitch_a.arrows(df_chance.EVENT_X, df_chance.EVENT_Y, df_chance.PASS_END_X, df_chance.PASS_END_Y, 
                         color='#dddddd', width=2, ax=ax_a)
            pitch_a.scatter(df_chance[df_chance.QUAL_STR.str.contains('210')].EVENT_X, df_chance[df_chance.QUAL_STR.str.contains('210')].EVENT_Y, 
                           s=150, c=HIF_GOLD, label='Assist', ax=ax_a)
            pitch_a.scatter(df_chance[~df_chance.QUAL_STR.str.contains('210')].EVENT_X, df_chance[~df_chance.QUAL_STR.str.contains('210')].EVENT_Y, 
                           s=120, c=HIF_BLUE, label='Key Pass', ax=ax_a)
            ax_a.legend(loc='lower center', bbox_to_anchor=(0.5, 0.02), ncol=2)
        st.pyplot(fig_a)
