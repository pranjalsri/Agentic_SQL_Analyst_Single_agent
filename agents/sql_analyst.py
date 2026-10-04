import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from utils.pick_llm import llm
from models.schema import AgentSchema, judgeSchema
from utils.database import get_connection, schema_details

#--------------------------Agent Code---------------------------------------------
def curate_question(state: AgentSchema) -> AgentSchema:
    user_question = state.user_question
    response = llm.invoke(f"Curate the following question for better understanding: {user_question}")
    state.curated_question = response.content
    return state

def prompt_query_context(state: AgentSchema) -> AgentSchema:

    curated_question = state.curated_question
    database_name = os.environ["SNOWFLAKE_DATABASE"]
    schema_name = os.environ["SNOWFLAKE_SCHEMA"]
    schema_info = schema_details(schema_name)

    # Constructing the prompt query for the agent to generate the SQL query
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language
    query into Snowflake SQL that can be executed on the database. You are provided
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    The active Snowflake database and schema are {database_name}.{schema_name}.
    Use only table and view names exactly as listed in the schema details; never
    invent or shorten an object name. Fully qualify every table/view in FROM and JOIN
    as {database_name}.{schema_name}.<exact listed object name>.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Return exactly one read-only SQL query beginning with SELECT or WITH and ending
    with a semicolon. Do not include explanations, markdown fences, or other text.
    
    User's Original Query: {curated_question}

    Database Schema Details:
    {schema_info}
    
    """    

    state.prompt_query_context = prompt

    return state


def _extract_sql_query(response: str) -> str:
    lines = response.strip().splitlines()
    query_start = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(r"^\s*(SELECT|WITH)\b", line, re.IGNORECASE)
        ),
        None,
    )
    if query_start is None:
        raise ValueError(
            "The LLM did not return a SQL query starting with SELECT or WITH."
        )

    query_text = "\n".join(
        line for line in lines[query_start:] if not line.strip().startswith("```")
    ).strip()

    quote: str | None = None
    index = 0
    while index < len(query_text):
        character = query_text[index]
        if quote:
            if character == quote:
                if index + 1 < len(query_text) and query_text[index + 1] == quote:
                    index += 1
                else:
                    quote = None
        elif character in {"'", '"'}:
            quote = character
        elif character == ";":
            return query_text[: index + 1].strip()
        index += 1

    raise ValueError(
        "The LLM response did not contain a semicolon-terminated SQL query; "
        "refusing to send ambiguous text to Snowflake."
    )


def generate_sql_query(state: AgentSchema) -> AgentSchema:
    prompt = state.prompt_query_context
    response = llm.invoke(prompt)
    state.generated_sql_query = _extract_sql_query(response.content)

    return state


def is_safe(state: AgentSchema) -> AgentSchema:
    sql_query = state.generated_sql_query
    llmjudge = llm.with_structured_output(judgeSchema)
    prompt = f"""You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision..here is the SQL query to evaluate:
    {sql_query} """
    
    response = llmjudge.invoke(f"{prompt}\n\nSQL Query: {sql_query}")
    state.is_safe = response.answer
    state.comments = response.comments

    return state


def cancellation(state: AgentSchema) -> AgentSchema:

    if not state.is_safe:
        state.final_answer = f"The generated SQL query is not safe to execute. Comments: {state.comments}"
    else:
        state.final_answer = "The generated SQL query is safe to execute."

    return state

def execute_sql_query(state: AgentSchema) -> AgentSchema:
    if state.is_safe:
        sql_query = state.generated_sql_query
        if not re.match(r"^\s*(SELECT|WITH)\b", sql_query, re.IGNORECASE):
            raise ValueError(
                "Refusing to execute SQL that does not start with SELECT or WITH."
            )
        connection = get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql_query)
                result = cursor.fetchall()
                state.sql_query_result = str(result)
            finally:
                cursor.close()
        finally:
            connection.close()
    else:
        state.sql_query_result = "SQL query execution skipped due to safety concerns."

    return state

def represent_final_answer(state: AgentSchema) -> AgentSchema:
    execution_result = state.sql_query_result
    curated_question = state.curated_question

    prompt = f"""You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear, and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
    Here is the execution result: {execution_result} \n
    Here is the user's original question: {curated_question}
    """

    llm_response = llm.invoke(prompt).content
    state.final_answer = llm_response
    state.messages = state.messages +[AIMessage(content=llm_response)]
    
    return state

#----------------------------------graph code---------------------------------------------

sql_agent_graph = StateGraph(AgentSchema)

# Nodes
sql_agent_graph.add_node("curate_ques", curate_question)
sql_agent_graph.add_node("prompt_query_context", prompt_query_context)
sql_agent_graph.add_node("generate_sql", generate_sql_query)
sql_agent_graph.add_node("is_safe_sql", is_safe)
sql_agent_graph.add_node("cancellation", cancellation)
sql_agent_graph.add_node("execute_sql_query", execute_sql_query)
sql_agent_graph.add_node("represent_final_answer", represent_final_answer)

# Edges
sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql")
sql_agent_graph.add_edge("generate_sql", "is_safe_sql")

# Codintional Edge Function
def is_safe_sql_edge(state: AgentSchema) -> str:
    if state.is_safe:
        return "execute_sql"
    return "canceled_sql"

sql_agent_graph.add_conditional_edges("is_safe_sql", is_safe_sql_edge,
                                      {
                                          "execute_sql": "execute_sql_query",
                                          "canceled_sql": "cancellation"
                                      })

sql_agent_graph.add_edge("cancellation", END)
sql_agent_graph.add_edge("execute_sql_query", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)

# Compile the Graph
sql_analyst = sql_agent_graph.compile()

if __name__ == "__main__":
    print(sql_analyst.get_graph().draw_mermaid())

    input_schema = {
        "messages": [],
        "user_question": "How many customers do we have in STG_DAILY_CUSTOMER table ?",
        "curated_question": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": False,
        "comments": "",
        "sql_query_result": "",
        "final_answer": ""
    }

    # Execute the Graph
    sql_analyst_response = sql_analyst.invoke(input_schema)
    print(sql_analyst_response['messages'])  # Print the final output of the graph execution
    print("********************************")

    print(sql_analyst_response['generated_sql_query'])  # Print the generated SQL query

    print("********************************")

    print(sql_analyst_response['sql_query_result'])  # Print the result of executing the SQL query

    print("********************************")

    print(sql_analyst_response['prompt_query_context'])  # Print the prompt query context