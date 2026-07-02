const BASE_URL = 'https://mechai-backend.delightfulsea-af823488.centralindia.azurecontainerapps.io'

export async function sendQuery({ query, session_id, user_type, user_id }) {
  const response = await fetch(`${BASE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id, user_type, user_id }),
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function getSessions(user_id) {
  const response = await fetch(`${BASE_URL}/sessions?user_id=${encodeURIComponent(user_id)}`)

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function getSessionHistory(session_id, user_id, user_type) {
  const params = new URLSearchParams({ user_id, user_type })
  const response = await fetch(
    `${BASE_URL}/sessions/${encodeURIComponent(session_id)}?${params.toString()}`
  )

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function getFaq() {
  const response = await fetch(`${BASE_URL}/faq`)

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}
