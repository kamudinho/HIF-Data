import streamlit as st

def vis_side(dp):
    st.write("### Min Profil")
    st.info(f"Bruger: {st.session_state.get('user')}")
    st.info(f"Rolle: {st.session_state.get('role')}")
