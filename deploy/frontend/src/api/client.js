const BASE_URL = import.meta.env.VITE_API_URL || 'https://project1-automotive-service-rag-agent.onrender.com'

export async function sendQuery({ query, session_id, user_type }) {
  const response = await fetch(`${BASE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id, user_type }),
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}
