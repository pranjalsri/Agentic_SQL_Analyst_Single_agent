import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.pick_llm import llm
from models.schema import AgentSchema,judgeSchema
from utils.database import schema_details

llm = llm
llmjudge = llm.with_structured_output(judgeSchema)
#sql_query = "select * from customers where customer_id = 123"

prompt = f"""You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision..here is the SQL query to evaluate:
    {sql_query} """


print(llmjudge.invoke(f"{prompt}\n\nSQL Query: {sql_query}"))
