import requests
import re
import os
# Import your execution system from Step 2
from database import get_db_schema, execute_query

OLLAMA_URL = "http://localhost:11434/api/generate"
# You can change 'llama3' to 'qwen2.5-coder:7b' if using that model
MODEL_NAME = "llama3" 

SYSTEM_PROMPT = """
You are a specialized Enterprise Text-to-SQL AI Agent for an SQLite database.
Your target users are non-technical business stakeholders who cannot write SQL or perform table joins.

RULES FOR QUERY GENERATION:
1. Identify database structural connections via explicit Foreign Key mappings.
2. If data spans across multiple tables, write clean explicit JOIN statements.
3. Use clear table aliases to prevent column name ambiguities (e.g., SELECT u.customer_name FROM orders o JOIN users u ON o.user_id = u.user_id).
4. Output ONLY valid executable read-only SQLite syntax wrapped inside a standard code block: ```sql <your query> 
```.
5. If the user request attempts to modify the database state using DROP, DELETE, UPDATE, INSERT, or ALTER, reply instantly with the word 'SECURITY_BLOCKED'.

Database Relational Schema Context:
{schema_context}
"""

def call_ollama(prompt):
    """Sends a request payload directly to your local Ollama server instance."""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    try:
        # Crucial Fix: Boosted timeout to 600 seconds (10 minutes) 
        # to ensure complex joins do not time out on local CPU hardware
        response = requests.post(OLLAMA_URL, json=payload, timeout=600)
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Ollama Connection Error: {str(e)}"

def extract_sql(raw_text):
    """Parses markdown code structures to extract the clean executable statement."""
    if "SECURITY_BLOCKED" in raw_text:
        return "SECURITY_BLOCKED"
    match = re.search(r"```sql\s+(.*?)\s+```", raw_text, re.DOTALL)
    return match.group(1).strip() if match else raw_text.strip()

def run_agent_loop(user_query, max_retries=3):
    """Runs a multi-turn self-healing loop to evaluate, execute, and repair SQL errors."""
    schema = get_db_schema()
    base_prompt = SYSTEM_PROMPT.format(schema_context=schema)
    current_prompt = f"User Request: {user_query}\nGenerate the matching SQLite statement."
    error_feedback = ""

    print(f"\n--- Starting Agent Execution Loop for: '{user_query}' ---")

    for attempt in range(max_retries):
        print(f"Agent Attempt {attempt + 1}/{max_retries}...")
        
        # Compile full context tracking past structural errors if any exist
        full_context = f"{base_prompt}\n{error_feedback}\n{current_prompt}"
        raw_output = call_ollama(full_context)
        clean_sql = extract_sql(raw_output)

        if clean_sql == "SECURITY_BLOCK" or "SECURITY_BLOCKED" in clean_sql:
            print("❌ Security Guardrail Triggered!")
            return {
                "status": "blocked", 
                "message": "Security Violation: Modifying operations are strictly restricted!"
            }

        print(f"Generated SQL: {clean_sql}")

        # Try executing query against the SQLite database engine (The Loop Verification step)
        execution_result = execute_query(clean_sql)
        
        if execution_result["status"] == "success":
            print("✅ Success! Query executed correctly.")
            return {
                "status": "success",
                "sql": clean_sql,
                "data": execution_result["data"],
                "attempts": attempt + 1
            }
        else:
            # Self-healing engine: Pack error context and feed it back to the AI model
            print(f"⚠️ Execution failed due to syntax error: {execution_result['message']}")
            error_feedback = f"\n[Attempt {attempt + 1} Failed] Your previous query: {clean_sql} raised database error: {execution_result['message']}. Re-evaluate schema constraints, fix column dependencies, and rewrite code completely."

    return {
        "status": "failed", 
        "message": f"Agent loop timed out after checking {max_retries} structural iterations."
    }

if __name__ == "__main__":
    # Test an analytical multi-table join prompt
    sample_request = "Show all purchases made by Alice Feng along with order status"
    outcome = run_agent_loop(sample_request)
    print("\nFinal Agent Response Structure:")
    print(outcome)