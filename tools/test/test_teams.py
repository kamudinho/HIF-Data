def create_h2h_plot(metrics, labels, t1, t2, n1, n2):
            fig = go.Figure()
            for name, stats in [(n1, t1), (n2, t2)]:
                c = TEAM_COLORS.get(name, {"primary": "#808080", "secondary": "#000000"})
                fig.add_trace(go.Bar(
                    name=name, x=labels, y=[stats[m] for m in metrics], 
                    marker_color=c["primary"],
                    marker_line_color=c["secondary"],
                    marker_line_width=2,
                    text=[fmt_val(stats[m]) for m in metrics], 
                    textposition='auto', showlegend=False
                ))
            
            logo_imgs = []
            # Vi justerer offset en lille smule (fra 0.17 til 0.18) 
            # for at de passer over de nu smallere søjler
            for idx in range(len(labels)):
                for s, offset in [(t1, -0.18), (t2, 0.18)]:
                    if pd.notnull(s['IMAGEDATAURL']):
                        logo_imgs.append(dict(
                            source=s['IMAGEDATAURL'], xref="x", yref="paper", 
                            x=idx + offset, y=1.02, sizex=0.07, sizey=0.07, 
                            xanchor="center", yanchor="bottom"
                        ))
            
            fig.update_layout(
                images=logo_imgs, 
                barmode='group', 
                bargap=0.4,       # Mellemrum mellem de forskellige metrikker (f.eks. Mål vs xG)
                bargroupgap=0.1,  # Mellemrum mellem Hold 1 og Hold 2 søjlen
                height=400, 
                margin=dict(t=70, b=20, l=10, r=10),
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False), 
                yaxis=dict(showgrid=False, showticklabels=False)
            )
            st.plotly_chart(fig, use_container_width=True)
