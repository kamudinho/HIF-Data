baker = PyPizza(
            params=params,
            min_range=[0]*len(params),
            max_range=[100]*len(params),
            background_color="#FFFFFF",
            straight_line_color="#222222",
            last_circle_color="#222222",
            last_circle_lw=1.5,
            other_circle_lw=0.5,
            other_circle_color="#DDDDDD",
            inner_circle_size=8,  # Sættes ned så felterne går tættere på midten
        )

        fig, ax = baker.make_pizza(
            values,
            figsize=(10, 10),
            color_blank_space="same",
            blank_alpha=0.4,
            param_location=110,
            kwargs_slices=dict(
                facecolor=slice_colors, edgecolor="#222222",
                zorder=1, linewidth=0.8
            ),
            kwargs_params=dict(
                color="#111111", fontsize=10, zorder=5,
                va="center", fontweight="bold"
            ),
            kwargs_values=dict(
                color="#FFFFFF", fontsize=9,
                zorder=3,
                bbox=dict(
                    edgecolor="#222222", facecolor="#111111",
                    boxstyle="round,pad=0.2", lw=0.8
                )
            )
        )

        ax.set_aspect('equal')
        fig.patch.set_facecolor('#FFFFFF')

        val_idx = 0
        for txt in ax.texts:
            pos = txt.get_position()
            if pos[1] < 100 and val_idx < len(values):
                txt.set_text(str(int(values[val_idx])))
                val_idx += 1

        logo_img = get_logo(logo_url)
        if logo_img:
            # Logoet placeres centreret på (0, 0) igen, nu hvor hullet er mindsket
            ax.add_artist(AnnotationBbox(OffsetImage(logo_img, zoom=0.50), (0, 0), frameon=True, 
                                          bboxprops=dict(facecolor='white', edgecolor='#222222', linewidth=1.5, boxstyle='circle'), 
                                          zorder=10))

        st.pyplot(fig, use_container_width=True)

        buf = BytesIO()
        fig.savefig(buf, format="png", facecolor="#FFFFFF", edgecolor='none', bbox_inches=None, dpi=300)
        
        with download_placeholder:
            st.download_button(
                label="Download",
                data=buf.getvalue(),
                file_name=f"Radar_{valgt_hold_navn}.png",
                mime="image/png"
            )
