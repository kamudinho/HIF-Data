def tegn_kampe(df, played):
        for _, row in df.iterrows():
            # 1. HENT DATO FRA MATCH_LOCALDATE
            dt_str = str(row.get('MATCH_LOCALDATE', ''))
            if not dt_str or dt_str == 'None':
                continue
            
            dt = pd.to_datetime(dt_str)
            dag_dk = danske_dage.get(dt.strftime('%A'), dt.strftime('%A'))
            maaned_dk = danske_maaneder.get(dt.strftime('%B'), dt.strftime('%B'))
            
            st.markdown(f"<div class='date-header'>{dag_dk.upper()} D. {dt.day}. {maaned_dk.upper()}</div>", unsafe_allow_html=True)
            
            # 2. HENT TID FRA MATCH_LOCALTIME
            # Vi tager de første 5 tegn fra f.eks. "18:30:00" -> "18:30"
            raw_time = str(row.get('MATCH_LOCALTIME', ''))
            if ":" in raw_time:
                display_time = raw_time[:5]
            else:
                display_time = "TBA"

            h_uuid = row['CONTESTANTHOME_OPTAUUID']
            a_uuid = row['CONTESTANTAWAY_OPTAUUID']
            h_n = id_to_name.get(h_uuid, row['CONTESTANTHOME_NAME'])
            a_n = id_to_name.get(a_uuid, row['CONTESTANTAWAY_NAME'])

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                c1.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{h_n}</div>", unsafe_allow_html=True)
                c2.image(hent_hold_logo(h_uuid), width=28)
                
                with c3:
                    if played:
                        # Hent scores fra dine data-kolonner
                        h_score = row.get('TOTAL_HOME_SCORE', 0)
                        a_score = row.get('TOTAL_AWAY_SCORE', 0)
                        st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(h_score)} - {int(a_score)}</span></div>", unsafe_allow_html=True)
                    else:
                        # Vis den korrekte display_time (f.eks. 15:00)
                        st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{display_time}</span></div>", unsafe_allow_html=True)
                
                c4.image(hent_hold_logo(a_uuid), width=28)
                c5.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{a_n}</div>", unsafe_allow_html=True)
