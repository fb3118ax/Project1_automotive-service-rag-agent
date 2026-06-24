const BASE_URL = 'https://mechai-backend.delightfulsea-af823488.centralindia.azurecontainerapps.io'

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
