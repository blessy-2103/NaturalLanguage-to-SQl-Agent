from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
# Import your tools from your previous database and agent components
from database import init_db_from_csv
from agent import run_agent_loop

app = FastAPI(
    title="NL-to-SQL Agent API Endpoint",
    description="FastAPI router driving a multi-turn local self-healing text-to-SQL engine using Llama 3."
)

# Define the expected JSON payload format
class QueryRequest(BaseModel):
    prompt: str

@app.on_event("startup")
def startup_event():
    """Triggers automatically when the API starts up to ensure the SQLite file is built and seeded."""
    # Ensure paths match your directory hierarchy layout (nl-sql-agent/data/business_data.csv)
    csv_source_path = os.path.join("..", "data", "business_data.csv")
    
    # Check alternate current working directory fallback if path resolution changes
    if not os.path.exists(csv_source_path):
        csv_source_path = os.path.join("data", "business_data.csv")
        
    print(f"Checking for database source data at: {csv_source_path}")
    print("Starting automated database seeding pipeline from CSV...")
    init_db_from_csv(csv_source_path)

@app.get("/")
def read_root():
    """Health check endpoint to verify backend service availability."""
    return {"status": "online", "message": "FastAPI Agent Core is up and running."}

@app.post("/api/ask")
def ask_agent(request: QueryRequest):
    """Primary endpoint routing interface queries straight to the pure Ollama agent loop."""
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt string cannot be blank.")
        
    # Execute the pure Ollama-reliant text-to-SQL agent workflow loop
    response = run_agent_loop(request.prompt)
    
    # Handle absolute failure if the model iterations time out completely
    if response.get("status") == "failed":
        raise HTTPException(status_code=500, detail=response.get("message"))
        
    return response