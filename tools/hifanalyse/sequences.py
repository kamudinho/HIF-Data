def vis_side(dp):
    # CSS til styling
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; }}
        </style>
    """, unsafe_allow_html=True)

    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df_raw.empty:
        return

    # 1. Datarens
    df = df_raw.copy()
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df = df.sort_values(['EVENT_TIMESTAMP', 'EVENT_TIMEMIN']).reset_index(drop=True)

    # 2. Find mål (Type 16)
    goals = df[df['EVENT_TYPEID'] == 16].copy()
    if goals.empty:
        st.info("Ingen mål fundet.")
        return
    
    goals['LABEL'] = goals.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1.2])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goals['LABEL'].unique(), label_visibility="collapsed")
        target_goal = goals[goals['LABEL'] == selected_label].iloc[0]
        
        # LOGIK-VASK: Vi tager kun de hændelser der hører til dette specifikke mål (GOAL_REF_ID)
        # Og vi filtrerer modstandere fra med det samme
        hif_team_id = target_goal['EVENT_CONTESTANT_OPTAUUID']
        active_seq = df[
            (df['SEQUENCEID'] == target_goal['SEQUENCEID']) & 
            (df['EVENT_CONTESTANT_OPTAUUID'] == hif_team_id) &
            (df['EVENT_TIMESTAMP'] <= target_goal['EVENT_TIMESTAMP'])
        ].copy().reset_index(drop=True)

        # Find assist (sidste HIF spiller før målscorer)
        scorer_name = target_goal['PLAYER_NAME'].split()[-1] if pd.notnull(target_goal['PLAYER_NAME']) else "HIF"
        assist_name = "Solo"
        assist_idx = -1
        
        for i in range(len(active_seq) - 2, -1, -1):
            if active_seq.loc[i, 'PLAYER_NAME'] != target_goal['PLAYER_NAME']:
                assist_name = active_seq.loc[i, 'PLAYER_NAME'].split()[-1]
                assist_idx = i
                break

        # UI: Stats
        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side">Målscorer</div>
                <div class="stat-value-side"><span style="color:{HIF_RED};">●</span> {scorer_name}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side">Assist / Næstsidst</div>
                <div class="stat-value-side"><span style="color:{ASSIST_BLUE};">●</span> {assist_name}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Tabel
        flow_list = []
        for i, r in active_seq.iterrows():
            p = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "?"
            ename = get_event_name(str(int(r['EVENT_TYPEID'])))
            disp_name = DK_NAMES.get(ename, ename)
            if r['EVENT_TYPEID'] == 16: disp_name = "MÅL ⚽"
            flow_list.append({"Spiller": p, "Aktion": disp_name})
            
        st.dataframe(pd.DataFrame(flow_list), use_container_width=True, hide_index=True, height=350)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        # HIF angriber mod højre
        should_flip = True if target_goal['RAW_X'] < 50 else False

        plot_points = []
        for i, r in active_seq.iterrows():
            cx = (100 - r['RAW_X'] if should_flip else r['RAW_X'])
            cy = (100 - r['RAW_Y'] if should_flip else r['RAW_Y'])
            
            plot_points.append({
                'x': cx, 'y': cy,
                'name': r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "",
                'is_goal': (r['EVENT_TYPEID'] == 16),
                'is_assist': (i == assist_idx)
            })

        # Tegn pile
        for i in range(1, len(plot_points)):
            p1, p2 = plot_points[i-1], plot_points[i]
            ax.annotate('', xy=(p2['x'], p2['y']), xytext=(p1['x'], p1['y']),
                        arrowprops=dict(arrowstyle='->', color='#cccccc', lw=2, alpha=0.5))

        # Tegn spillere
        for pt in plot_points:
            color = HIF_RED if pt['is_goal'] else (ASSIST_BLUE if pt['is_assist'] else '#999999')
            pitch.scatter(pt['x'], pt['y'], s=150, color=color, edgecolors='white', ax=ax, zorder=5)
            ax.text(pt['x'], pt['y'] + 3, pt['name'], fontsize=10, ha='center', fontweight='bold')

        st.pyplot(fig)
