import { useState, useCallback, useRef } from 'react'
import { sendQuery } from '../api/client'

function newSessionId() {
  return crypto.randomUUID()
}

export function useChat() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [slowServer, setSlowServer] = useState(false)
  const [userType, setUserType] = useState('owner')
  const sessionId = useRef(newSessionId())
  const slowTimer = useRef(null)

  const send = useCallback(async (query) => {
    if (!query.trim() || loading) return

    const userMsg = { role: 'user', content: query }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    setSlowServer(false)

    slowTimer.current = setTimeout(() => setSlowServer(true), 5000)

    try {
      const data = await sendQuery({
        query,
        session_id: sessionId.current,
        user_type: userType,
      })

      const isGuardrail = data.guardrail_response !== ''

      const botMsg = {
        role: 'bot',
        content: isGuardrail ? data.guardrail_response : data.answer,
        confidence_score: isGuardrail ? null : data.confidence_score,
        citations: isGuardrail ? [] : data.citations,
        guardrail: isGuardrail,
      }

      setMessages(prev => [...prev, botMsg])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'bot',
        content: 'Something went wrong. Please try again.',
        error: true,
        citations: [],
        confidence_score: null,
        guardrail: false,
      }])
    } finally {
      clearTimeout(slowTimer.current)
      setLoading(false)
      setSlowServer(false)
    }
  }, [loading, userType])

  const newConversation = useCallback(() => {
    sessionId.current = newSessionId()
    setMessages([])
    setLoading(false)
    setSlowServer(false)
  }, [])

  return { messages, loading, slowServer, userType, setUserType, send, newConversation }
}
