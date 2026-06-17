import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Set up sys.path for importing app modules when running directly
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from app.database.vector_store import get_vector_store

# Load environment variables from backend/.env
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent
env_path = backend_dir / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

def is_greeting(query: str) -> bool:
    """Detects if a user query is a simple greeting or introductory question."""
    clean_query = query.strip().lower().rstrip("?").rstrip("!").rstrip(".")
    greetings = {
        "hi", "hello", "hey", "greetings", "good morning", "good afternoon", 
        "good evening", "howdy", "hola", "yo", "what's up", "whats up", "hey there"
    }
    
    # Check if exact match
    if clean_query in greetings:
        return True
        
    # Check if asking about the system itself
    system_questions = {
        "who are you", "what is this", "what do you do", "what can you do",
        "how do i use this", "help", "info"
    }
    if clean_query in system_questions:
        return True
        
    return False

def get_greeting_response() -> str:
    """Returns a default static greeting."""
    return (
        "Hello! I am your AI Assistant. I am here to help you search, filter, and analyze "
        "the candidate database. The dataset consists of 5,000 candidate profiles from the "
        "2020 to 2025 graduation batches.\n\n"
        "How can I assist you today?"
    )

def classify_query(query: str, api_key: str, model_name: str) -> str:
    """Classifies the query as GREETING, ANALYTICAL, or SEMANTIC using the LLM."""
    if is_greeting(query):
        return "GREETING"
        
    # If API key is not configured, we cannot call classification LLM
    if not api_key or api_key.strip() == "" or "your_groq_api_key_here" in api_key:
        return "SEMANTIC"
        
    try:
        llm = ChatGroq(
            groq_api_key=api_key,
            model=model_name,
            temperature=0.0,
            max_tokens=15
        )
        prompt = (
            "You are a routing agent for a candidate sourcing database.\n"
            "Classify the user query into one of the following categories:\n"
            "1. 'ANALYTICAL': For queries asking for database statistics, counts, averages, calculations, aggregates, "
            "or group comparisons (e.g., 'how many candidates graduated from BITS Goa?', 'what is the average CGPA?', "
            "'who has the highest salary?', 'compare python vs java candidate counts').\n"
            "2. 'SEMANTIC': For queries searching for candidate resumes based on specific skills, roles, "
            "or locations (e.g., 'find React developers', 'show candidates in Delhi', 'list Python engineers').\n"
            "3. 'OUT_OF_DOMAIN': For queries that are completely unrelated to candidate profiles, recruitment, job sourcing, "
            "hiring stats, or our candidate database (e.g. general knowledge questions, writing code, essays, recipes, "
            "geography, history, math equations, or anything not about the database candidate pool).\n\n"
            f"Query: \"{query}\"\n\n"
            "Respond with exactly one word, either 'ANALYTICAL', 'SEMANTIC', or 'OUT_OF_DOMAIN'."
        )
        response = llm.invoke(prompt)
        res_text = str(response.content).strip().upper()
        if "ANALYTICAL" in res_text:
            return "ANALYTICAL"
        elif "OUT_OF_DOMAIN" in res_text:
            return "OUT_OF_DOMAIN"
        return "SEMANTIC"
    except Exception as e:
        print(f"Error in query classification: {e}")
        return "SEMANTIC"

def execute_structured_rag(query: str, api_key: str, model_name: str) -> str:
    """Generates a SQLite query, runs it globally on the database, and synthesizes the final answer."""
    from app.database.sql_db import run_sql_query
    
    schema_info = """
    Table Name: candidates
    Columns & Types:
    - candidate_id (INTEGER)
    - full_name (TEXT)
    - gender (TEXT)
    - age (INTEGER)
    - graduation_year (INTEGER)
    - college (TEXT)
    - degree (TEXT)
    - branch (TEXT)
    - cgpa (REAL)
    - backlogs (INTEGER)
    - gap_year (TEXT) - 'Yes' or 'No'
    - prior_internship (TEXT) - 'Yes' or 'No'
    - projects_count (INTEGER)
    - certifications_count (INTEGER)
    - top_skills (TEXT) - skills separated by pipe e.g. 'React | Python | SQL'
    - platform (TEXT)
    - company_applied (TEXT)
    - sector (TEXT)
    - job_role (TEXT)
    - work_type (TEXT)
    - job_location (TEXT)
    - application_date (TEXT)
    - hiring_stage (TEXT)
    - interview_rounds (INTEGER)
    - response_time_days (INTEGER)
    - offered_salary_inr (REAL)
    - linkedin_connections (INTEGER)
    - profile_completion_pct (INTEGER)
    - linkedin_premium (TEXT) - 'Yes', 'No', or 'N/A'
    - referral_applied (TEXT) - 'Yes' or 'No'
    """
    
    try:
        llm = ChatGroq(
            groq_api_key=api_key,
            model=model_name,
            temperature=0.0,
            max_tokens=256
        )
        
        sql_generation_prompt = (
            "You are a SQLite query generator. Based on the following schema:\n"
            f"{schema_info}\n"
            f"Generate a single valid SQLite SQL query to answer the question: '{query}'.\n"
            "Guidelines:\n"
            "- Ensure the query is read-only (SELECT statements only).\n"
            "- For matching specific skills inside pipe-separated text, use LIKE (e.g. `top_skills LIKE '%Python%'`).\n"
            "- Use clean SQLite syntax.\n"
            "- Return ONLY the SQLite SQL query code block starting with ```sql and ending with ```. Do not add any explanation."
        )
        
        response = llm.invoke(sql_generation_prompt)
        sql_text = str(response.content).strip()
        
        # Extract SQL from markdown code block
        if "```sql" in sql_text:
            sql_text = sql_text.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql_text:
            sql_text = sql_text.split("```")[1].split("```")[0].strip()
            
        print(f"Generated SQL: {sql_text}")
        
        # Execute query
        results, err = run_sql_query(sql_text)
        
        # Self-correction loop if SQL query fails
        if err:
            print(f"SQL execution error: {err}. Attempting self-correction...")
            correction_prompt = (
                f"The generated query: {sql_text}\n"
                f"Failed with SQLite error: {err}\n"
                "Please rewrite the query correctly. Return ONLY the code block starting with ```sql."
            )
            response = llm.invoke(correction_prompt)
            sql_text = str(response.content).strip()
            if "```sql" in sql_text:
                sql_text = sql_text.split("```sql")[1].split("```")[0].strip()
            elif "```" in sql_text:
                sql_text = sql_text.split("```")[1].split("```")[0].strip()
            print(f"Corrected SQL: {sql_text}")
            results, err = run_sql_query(sql_text)
            
        if err:
            raise Exception(f"SQL Execution Error: {err}")
            
        # Format results into tabular text
        if not results:
            results_summary = "No records matched the SQL query."
        else:
            columns = list(results[0].keys())
            header = " | ".join(columns)
            separator = " | ".join(["---"] * len(columns))
            rows_list = []
            for row in results[:30]:  # Limit rows in prompt to fit token constraints
                rows_list.append(" | ".join(str(row.get(col, "")) for col in columns))
            results_summary = f"{header}\n{separator}\n" + "\n".join(rows_list)
            if len(results) > 30:
                results_summary += f"\n*(showing top 30 of {len(results)} matches)*"
                
        # Synthesize final answer based on data findings
        synthesis_llm = ChatGroq(
            groq_api_key=api_key,
            model=model_name,
            temperature=0.2,
            max_tokens=512
        )
        synthesis_prompt = (
            "You are an AI Assistant. Present the following SQL candidate database analysis results in a clean, professional, "
            f"and helpful response to the user's query: '{query}'.\n\n"
            f"Query Results:\n{results_summary}\n\n"
            "Format your response using bold headings and bullet points where appropriate. Do not reference SQL query "
            "details or SQLite syntax in your response, focus purely on reporting the candidate data findings.\n"
            "IMPORTANT: If the user's question is completely irrelevant to candidate profiles, recruitment, or job sourcing, "
            "you MUST reply exactly with: 'I'm unable to answer on that topic. I can only assist with questions relevant to the candidate and recruitment database.'"
        )
        
        final_response = synthesis_llm.invoke(synthesis_prompt)
        return str(final_response.content)
        
    except Exception as e:
        print(f"SQL agent execution failed: {e}. Falling back to similarity search...")
        raise e

def generate_response(query: str, k: int = 5) -> str:
    """
    Retrieves candidate information and generates a response.
    Routes queries to greetings, SQLite (for analytical aggregates),
    or ChromaDB vector search (for semantic profile sourcing).
    """
    # Load Groq configs
    api_key = os.getenv("GROQ_API_KEY", "")
    model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # 1. Quick greeting check
    if is_greeting(query):
        if not api_key or api_key.strip() == "" or "your_groq_api_key_here" in api_key:
            return get_greeting_response()
            
        try:
            llm = ChatGroq(
                groq_api_key=api_key,
                model=model_name,
                temperature=0.7,
                max_tokens=512
            )
            response = llm.invoke([
                ("system", "You are an AI Assistant. Greet the user professionally and briefly. "
                           "Explain that you assist with searching, filtering, and analyzing the candidate database. "
                           "State clearly that the database consists of 5,000 candidate profiles from the 2020 to 2025 graduation batches. "
                           "Do not include any examples of queries, candidate names, or invent any personal names. "
                           "Keep the response under three sentences."),
                ("human", query)
            ])
            return str(response.content)
        except Exception:
            return get_greeting_response()

    # 2. Classify query (ANALYTICAL, SEMANTIC, or OUT_OF_DOMAIN)
    category = classify_query(query, api_key, model_name)
    print(f"Query classification result: {category}")
    
    if category == "OUT_OF_DOMAIN":
        return "I'm unable to answer on that topic. I can only assist with questions relevant to the candidate and recruitment database."
    
    if category == "ANALYTICAL":
        try:
            return execute_structured_rag(query, api_key, model_name)
        except Exception as e:
            print(f"SQL Agent failed: {e}. Executing fallback Vector Search.")

    # 3. Vector Similarity Search
    try:
        db = get_vector_store()
        print(f"Retrieving top {k} matching candidates for query: '{query}'...")
        docs = db.similarity_search(query, k=k)
    except Exception as e:
        return f"Error retrieving data from ChromaDB vector store: {e}"

    if not docs:
        return "No candidate profiles found in the vector database matching your search."

    # Format candidate contexts for prompt
    context_blocks = []
    for idx, doc in enumerate(docs):
        context_blocks.append(f"[Candidate Profile {idx + 1}]\n{doc.page_content}")
    context = "\n\n".join(context_blocks)

    # Handle unconfigured API Key gracefully
    if not api_key or api_key.strip() == "" or "your_groq_api_key_here" in api_key:
        return (
            "[WARNING] GROQ_API_KEY is not set in backend/.env yet!\n\n"
            "Here is the raw data retrieved from ChromaDB for your query:\n"
            "==================================================\n"
            f"{context}\n"
            "=================================================="
        )

    # Initialize Groq Chat model
    llm = ChatGroq(
        groq_api_key=api_key,
        model=model_name,
        temperature=0.1,  # Low temperature to keep outputs factual
        max_tokens=1024
    )

    # Prompt Engineering
    system_instruction = (
        "You are an AI Assistant. Your objective is to answer the user's questions "
        "about candidate profiles. Base your response ONLY on the candidates provided below in the context. "
        "Summarize the findings clearly, comparing candidates if relevant, and present your output using "
        "clean bullet points and bold headers. Do not mention or hallucinate details not found in the context.\n"
        "IMPORTANT: If the user's question is completely irrelevant to candidate profiles, recruitment, or job sourcing, "
        "you MUST reply exactly with: 'I'm unable to answer on that topic. I can only assist with questions relevant to the candidate and recruitment database.'\n\n"
        f"--- Candidate Context ---\n{context}\n-------------------------"
    )

    try:
        print(f"Sending query and context to Groq model '{model_name}'...")
        response = llm.invoke([
            ("system", system_instruction),
            ("human", query)
        ])
        return str(response.content)
    except Exception as e:
        return (
            f"Error calling Groq API: {e}\n\n"
            f"Here is the database context retrieved:\n{context}"
        )

if __name__ == "__main__":
    # Local quick test run
    print("\n--- Running generator.py Local Test ---")
    
    # Test 1: Analytical Query
    test_query_1 = "How many candidates graduated from BITS Goa?"
    print(f"\nTest 1 Query: {test_query_1}")
    reply_1 = generate_response(test_query_1, k=2)
    print("Test 1 Reply:")
    print(reply_1)

    # Test 2: Semantic Query
    test_query_2 = "Find Python and React developers"
    print(f"\nTest 2 Query: {test_query_2}")
    reply_2 = generate_response(test_query_2, k=2)
    print("Test 2 Reply:")
    print(reply_2)

    # Test 3: Out of Domain Query
    test_query_3 = "Can you write a python script to reverse a string?"
    print(f"\nTest 3 Query: {test_query_3}")
    reply_3 = generate_response(test_query_3, k=2)
    print("Test 3 Reply:")
    print(reply_3)
