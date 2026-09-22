#HIF-Data/data/sql/db_config.py
"""
Ét sted for Snowflake-databasenavnet. Det stod tidligere hardkodet som
DB = "KLUB_HVIDOVREIF.AXIS" i seks forskellige filer (head.py, kampe.py,
liga_spillere.py [som db_navn-parameter, den er allerede fleksibel],
opta_queries.py, queries.py, skud_data.py). Skifter I nogensinde database-
eller schemanavn, retter I det ét sted i stedet for at lede seks steder.

Brug: from data.sql.db_config import DB
"""

DB = "KLUB_HVIDOVREIF.AXIS"
