# TalentAI Candidate Sourcing RAG App

A modern, high-performance candidate sourcing application powered by local vector search (**ChromaDB**), local semantic embeddings (**sentence-transformers**), and reasoning models (**Groq LLM**). It features a beautiful, glassmorphic UI with persistent chat history.

---

## 🛠️ Prerequisites

Ensure you have the following installed on your machine:
* **Python**: `3.10` or higher
* **Node.js**: `18.0` or higher (with `npm`)

---

## 🚀 How to Run the Application

Follow these steps to set up and run the backend API and the frontend dev server.

### 1. Backend Setup & Run

1. **Navigate to the Backend Directory**:
   ```bash
   cd backend
   ```

2. **Create and Activate a Virtual Environment (Recommended)**:
   * **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   * **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**:
   Create a `.env` file in the `backend` directory and add your Groq API key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.1-8b-instant
   ```
   *(Note: If the Groq key is omitted or invalid, the backend will gracefully fallback to returning local vector data directly to prevent system crashes.)*

5. **Start the FastAPI Backend Server**:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The backend server will run at `http://127.0.0.1:8000`. You can inspect the interactive API documentation at `http://127.0.0.1:8000/docs`.

---

### 2. Frontend Setup & Run

1. **Open a New Terminal Window** and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. **Install Frontend Dependencies**:
   ```bash
   npm install
   ```

3. **Start the React Development Server**:
   ```bash
   npm start
   ```

4. **Access the App**:
   The application will automatically compile and open in your default browser at:
   👉 **`http://localhost:3000`**

---

## 📂 Project Structure

```
hiring_data_rag/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── embeddings.py  # Local sentence-transformers loader
│   │   │   ├── generator.py   # Query routing & LLM response builder
│   │   │   └── ingestion.py   # Dataset ingestion script
│   │   ├── database/
│   │   │   └── vector_store.py# ChromaDB client initialization
│   │   └── main.py            # FastAPI entrypoint and routes
│   └── requirements.txt       # Python dependencies
├── data/
│   ├── raw/                   # CSV candidate dataset (5k profiles)
│   └── processed_index/       # Local SQLite & ChromaDB binary index files (untracked)
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── services/
│   │   │   └── api.js         # API client connection functions
│   │   ├── App.js             # Main layout, chat logic & state
│   │   └── index.css          # Core styling system (CSS)
│   └── package.json           # Frontend dependencies
├── .gitignore                 # Git ignore file
└── README.md                  # This guide
```
