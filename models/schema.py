from operator import add

from pydantic import BaseModel, Field
from typing import Annotated, Literal

class AgentSchema(BaseModel):
    messages: Annotated[list, add] = Field(default_factory=list, description="The list of messages exchanged between the user and the agent.")
    user_question:str = Field(..., description="The original question asked by the user.")
    curated_question: str = ""
    prompt_query_context: str = ""
    is_safe: bool = False
    generated_sql_query: str = ""
    sql_query_result: str = ""
    comments: str = ""
    final_answer: str = ""

class judgeSchema(BaseModel):
    answer:Literal[True,False] = Field(..., description="Indicates whether the generated SQL is safe to execute or not")
    comments:str = Field(..., description="Any comments or feedback provided by the agent regarding the generated SQL query.")