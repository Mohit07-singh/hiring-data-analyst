import os
import sys
import pandas as pd
from pathlib import Path
from langchain_core.documents import Document

# Set up sys.path for importing app modules
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from app.database.vector_store import get_vector_store

def get_csv_path() -> Path:
    """Resolves the absolute path to the raw dataset CSV file."""
    # ingestion.py is at: rag-web-app/backend/app/core/ingestion.py
    # We want: rag-web-app/data/raw/fresher_hiring_india_dataset.csv
    current_file = Path(__file__).resolve()
    workspace_root = current_file.parent.parent.parent.parent
    csv_path = workspace_root / "data" / "raw" / "fresher_hiring_india_dataset.csv"
    return csv_path

def load_raw_data():
    """Loads the raw hiring CSV dataset using pandas."""
    csv_path = get_csv_path()
    
    print(f"Resolving raw data file path: {csv_path}")
    if not csv_path.exists():
        print(f"Error: Raw data file not found at {csv_path}")
        return None
        
    try:
        print("Loading CSV data...")
        df = pd.read_csv(csv_path)
        print(f"Successfully loaded CSV data!")
        print(f"Dataset Dimensions: {df.shape[0]} rows, {df.shape[1]} columns")
        return df
    except Exception as e:
        print(f"Failed to load CSV file. Error: {e}")
        return None

def clean_val(val):
    """Helper to convert missing values to N/A or strings safely."""
    if pd.isna(val):
        return "N/A"
    return str(val)

def row_to_profile_text(row) -> str:
    """Compiles a row of candidate details into a semantic paragraph."""
    profile = (
        f"Candidate: {clean_val(row.get('full_name'))} (ID: {clean_val(row.get('candidate_id'))}). "
        f"Gender: {clean_val(row.get('gender'))}, Age: {clean_val(row.get('age'))}. "
        f"Education: Graduated in {clean_val(row.get('graduation_year'))} from {clean_val(row.get('college'))} "
        f"with a {clean_val(row.get('degree'))} in {clean_val(row.get('branch'))}. "
        f"CGPA is {clean_val(row.get('cgpa'))} with {clean_val(row.get('backlogs'))} backlogs and {clean_val(row.get('gap_year'))} gap year. "
        f"Prior Internship: {clean_val(row.get('prior_internship'))}. Academic Projects count: {clean_val(row.get('projects_count'))}, Certifications count: {clean_val(row.get('certifications_count'))}. "
        f"Skills: {clean_val(row.get('top_skills'))}. "
        f"Application Details: Applied on {clean_val(row.get('application_date'))} for {clean_val(row.get('job_role'))} ({clean_val(row.get('work_type'))}) at {clean_val(row.get('company_applied'))} in the {clean_val(row.get('sector'))} sector. Location: {clean_val(row.get('job_location'))}. "
        f"Status: Hiring stage is '{clean_val(row.get('hiring_stage'))}' after {clean_val(row.get('interview_rounds'))} rounds. "
        f"Other Details: Offered Salary is INR {clean_val(row.get('offered_salary_inr'))}. LinkedIn Connections: {clean_val(row.get('linkedin_connections'))}, Profile Completion: {clean_val(row.get('profile_completion_pct'))}%, Premium: {clean_val(row.get('linkedin_premium'))}, Referral: {clean_val(row.get('referral_applied'))}."
    )
    return profile

def chunk_data_into_documents(df: pd.DataFrame):
    """Converts each candidate row in the DataFrame into a LangChain Document object."""
    print("Converting candidate rows into document chunks...")
    documents = []
    
    for idx, row in df.iterrows():
        text_content = row_to_profile_text(row)
        
        # Build clean metadata structure for the vector store
        metadata = {
            "candidate_id": int(row.get("candidate_id", idx)),
            "full_name": clean_val(row.get("full_name")),
            "college": clean_val(row.get("college")),
            "degree": clean_val(row.get("degree")),
            "branch": clean_val(row.get("branch")),
            "cgpa": float(row.get("cgpa", 0.0)) if pd.notna(row.get("cgpa")) else 0.0,
            "top_skills": clean_val(row.get("top_skills")),
            "company_applied": clean_val(row.get("company_applied")),
            "job_role": clean_val(row.get("job_role")),
            "job_location": clean_val(row.get("job_location")),
            "hiring_stage": clean_val(row.get("hiring_stage"))
        }
        
        # Clean any invalid NaN strings from metadata
        metadata = {k: v for k, v in metadata.items() if v != "NaN" and v is not None}
        
        doc = Document(page_content=text_content, metadata=metadata)
        documents.append(doc)
        
    print(f"Successfully chunked {len(documents)} candidate profiles.")
    return documents

def save_to_vector_store(documents):
    """Saves the document chunks to ChromaDB database in data/processed_index."""
    db = get_vector_store()
    
    # We clear the existing collection to prevent duplicates if re-ingesting
    try:
        print("Clearing existing database collection...")
        # Access underlying client to delete the collection
        client = db._client
        client.delete_collection("candidates")
        # Re-initialize vector store
        db = get_vector_store()
    except Exception as e:
        print(f"Note (normal if database was empty): {e}")

    batch_size = 200
    total_docs = len(documents)
    print(f"Indexing {total_docs} candidates in batches of {batch_size}...")
    
    for i in range(0, total_docs, batch_size):
        batch = documents[i:i + batch_size]
        db.add_documents(batch)
        print(f"Indexed records {i + 1} to {min(i + batch_size, total_docs)}...")
        
    print("Database indexing complete!")

if __name__ == "__main__":
    df = load_raw_data()
    if df is not None:
        docs = chunk_data_into_documents(df)
        save_to_vector_store(docs)
