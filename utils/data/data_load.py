import snowflake.connector

@st.cache_resource
def _connect():
    """Opretter og cacher den primære Snowflake-forbindelse."""
    return snowflake.connector.connect(
        account=st.secrets["connections"]["snowflake"]["account"],
        user=st.secrets["connections"]["snowflake"]["user"],
        password=st.secrets["connections"]["snowflake"]["password"],
        warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
        database=st.secrets["connections"]["snowflake"]["database"],
        schema=st.secrets["connections"]["snowflake"]["schema"],
        role=st.secrets["connections"]["snowflake"]["role"]
    )

def _get_snowflake_conn(force_new=False):
    """
    Returnerer en forbindelse. Hvis force_new er True, oprettes en ny 
    forbindelse til brug i parallelle tråde.
    """
    if force_new:
        return snowflake.connector.connect(
            account=st.secrets["connections"]["snowflake"]["account"],
            user=st.secrets["connections"]["snowflake"]["user"],
            password=st.secrets["connections"]["snowflake"]["password"],
            warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
            database=st.secrets["connections"]["snowflake"]["database"],
            schema=st.secrets["connections"]["snowflake"]["schema"],
            role=st.secrets["connections"]["snowflake"]["role"]
        )
    return _connect()
