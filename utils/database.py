import os

import snowflake.connector
from dotenv import load_dotenv
from snowflake.connector import SnowflakeConnection

load_dotenv()


def get_connection() -> SnowflakeConnection:
    required_settings = (
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
    )
    missing_settings = [
        setting for setting in required_settings if not os.getenv(setting)
    ]
    if missing_settings:
        raise RuntimeError(
            "Missing required Snowflake settings: " + ", ".join(missing_settings)
        )

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def _quote_identifier(identifier: str) -> str:
	return '"' + identifier.replace('"', '""') + '"'


def schema_details(schema_name: str) -> str:
	schema_info_context = f"Database Schema: {schema_name}\n"
	connection = get_connection()

	try:
		cursor = connection.cursor()
		try:
			cursor.execute(
				"SELECT TABLE_SCHEMA, TABLE_NAME "
				"FROM INFORMATION_SCHEMA.TABLES "
				"WHERE UPPER(TABLE_SCHEMA) = UPPER(%s)",
				(schema_name,),
			)
			tables = cursor.fetchall()

			for table_schema, table_name in tables:
				schema_info_context += f"\nTable: {table_name}\n"
				cursor.execute(
					"SELECT COLUMN_NAME, DATA_TYPE "
					"FROM INFORMATION_SCHEMA.COLUMNS "
					"WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
					(table_schema, table_name),
				)

				for column_name, data_type in cursor.fetchall():
					schema_info_context += (
						f"  Column: {column_name}, Data Type: {data_type}\n"
					)

				qualified_table = (
					f"{_quote_identifier(table_schema)}."
					f"{_quote_identifier(table_name)}"
				)
				cursor.execute(f"SELECT * FROM {qualified_table} LIMIT 5")
				schema_info_context += "  Sample Data:\n"
				for row in cursor.fetchall():
					schema_info_context += f"    {row}\n"
		finally:
			cursor.close()
	finally:
		connection.close()

	return schema_info_context


if __name__ == "__main__":
	result = schema_details("staging")
	with open("schema_details.txt", "w", encoding="utf-8") as file:
		file.write(result)