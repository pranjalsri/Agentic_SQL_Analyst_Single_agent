from langchain_ollama import ChatOllama
from dotenv import load_dotenv  
load_dotenv()  # Load environment variables from .env file

MODEL_NAME = "qwen2.5-coder:7b"

llm = ChatOllama(model=MODEL_NAME, temperature=0)


#response = llm.invoke("TELL ME THE LYRICS OF COCTAIL MOVIEW SONG YARA TERE")
#print(response)
