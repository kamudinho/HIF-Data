# --- 1. KONFIGURATION & CSS ---
st.set_page_config(
    page_title="HIF Performance Hub", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        /* 1. FJERN TOP-PADDING PÅ HELE SIDEN */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
        
        /* 2. FJERN TOP-PADDING I SIDEBAREN */
        [data-testid="stSidebarUserContent"] {
            padding-top: 0.5rem;
        }

        /* 3. STRAM OP OMKRING LOGO OG NAVN */
        [data-testid="stSidebar"] img {
            margin-bottom: -10px;
        }
        
        /* 4. SIDEBAR BREDDE OG GENEREL STYLING */
        [data-testid="stSidebar"] {
            min-width: 260px;
            max-width: 320px;
        }

        /* Gør radio-buttons mere kompakte */
        div.row-widget.stRadio > div {
            background-color: #f8f9fb;
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #eceef1;
            margin-top: -10px; /* Flytter menuen tættere på overskriften */
        }

        /* Justering af divider-afstanden */
        hr {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)
