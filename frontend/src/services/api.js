const BASE_URL = "http://127.0.0.1:8000/api";

/**
 * Checks the connection status of the backend FastAPI server and database.
 * @returns {Promise<{status: string, database?: string, indexed_candidates?: number, error?: string}>}
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${BASE_URL}/health`, {
      method: "GET",
      headers: { "Accept": "application/json" }
    });
    if (!response.ok) {
      throw new Error(`Health check responded with status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("API checkHealth failed:", error);
    return { status: "unhealthy", database: "disconnected", error: error.message };
  }
}

/**
 * Sends a natural language query to the RAG backend API.
 * @param {string} query - The search query text.
 * @param {number} k - The number of candidates to retrieve.
 * @returns {Promise<{response: string}>}
 */
export async function queryRAG(query, k = 5) {
  const response = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    body: JSON.stringify({ query, k })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server error: ${response.status}`);
  }

  return await response.json();
}
