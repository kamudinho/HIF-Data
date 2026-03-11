# --- TAB 3: ASSIST-ZONER (KOMPLET VISUALISERING) ---
    with tab3:
        col_viz_z, col_ctrl_z = st.columns([1.8, 1])
        
        df_goals = df_assists[df_assists['is_assist'] == 1].copy()
        total_goals = len(df_goals)
        
        zone_stats = {}
        for zone in ZONE_BOUNDS.keys():
            z_data = df_goals[df_goals['Zone'] == zone]
            count = len(z_data)
            pct = (count / total_goals * 100) if total_goals > 0 else 0
            # Find topspiller i zonen
            top_p = z_data['ASSIST_PLAYER'].mode().iloc[0] if not z_data.empty else "-"
            # Forkort efternavn hvis det er for langt til banen
            display_name = top_p.split(' ')[-1] if top_p != "-" else "-"
            
            zone_stats[zone] = {'count': count, 'pct': pct, 'top': top_p, 'short_top': display_name}

        with col_ctrl_z:
            st.markdown("**DETALJERET ZONEOVERSIGT**")
            z_df = pd.DataFrame([
                {'Zone': k, 'Assists': v['count'], 'Pct': f"{v['pct']:.1f}%", 'Top Spiller': v['top']}
                for k, v in zone_stats.items()
                if v['count'] > 0
            ]).sort_values('Assists', ascending=False)
            
            st.dataframe(z_df, hide_index=True, use_container_width=True)

        with col_viz_z:
            max_val = max([v['count'] for v in zone_stats.values()]) if total_goals > 0 else 1
            cmap = plt.cm.YlOrRd 

            pitch_z = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig_z, ax_z = pitch_z.draw(figsize=(8, 10))
            ax_z.set_ylim(50, 105)

            for name, bounds in ZONE_BOUNDS.items():
                if bounds["y"][1] <= 50: continue
                
                y_min_d = max(bounds["y"][0], 50)
                rect_h = bounds["y"][1] - y_min_d
                
                stats = zone_stats[name]
                color_val = stats['count'] / max_val
                face_color = cmap(color_val) if stats['count'] > 0 else '#f9f9f9'
                
                rect = Rectangle((bounds["x"][0], y_min_d), bounds["x"][1] - bounds["x"][0], rect_h,
                                 edgecolor='black', linestyle='--', facecolor=face_color, alpha=0.7)
                ax_z.add_patch(rect)

                # --- TEKST I ZONEN (Navn, Antal, Pct, Topspiller) ---
                # Vi bruger en f-string til at lave flere linjer
                z_text = (f"$\\mathbf{{{name.replace('Zone ', 'Z')}}}$\n"
                          f"{stats['count']} ({stats['pct']:.1f}%)\n"
                          f"{stats['short_top']}")
                
                ax_z.text(bounds["x"][0] + (bounds["x"][1] - bounds["x"][0])/2, 
                          y_min_d + rect_h/2, z_text, 
                          ha='center', va='center', fontsize=7, 
                          color='black' if color_val < 0.6 else 'white',
                          linespacing=1.5)

            st.pyplot(fig_z, use_container_width=True)
