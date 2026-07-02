import { useState, useCallback, useRef } from 'react'
import { sendQuery, getSessionHistory } from '../api/client'
import { getUserId } from '../lib/userId'

function newSessionId() {
  return crypto.randomUUID()
}

export function useChat() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [slowServer, setSlowServer] = useState(false)
  const [userType, setUserType] = useState(null)
  const sessionId = useRef(newSessionId())
  const userId = useRef(getUserId())
  const slowTimer = useRef(null)

  const selectMode = useCallback((mode) => {
    setUserType(mode)
    sessionId.current = newSessionId()
    setMessages([])
  }, [])

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
        user_id: userId.current,
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
    setUserType(null)
    sessionId.current = newSessionId()
    setMessages([])
    setLoading(false)
    setSlowServer(false)
  }, [])

  // Loads a past conversation from Cosmos and resumes it, badges/citations included.
  const loadConversation = useCallback(async (session_id, loadedUserType) => {
    setLoading(true)
    try {
      const data = await getSessionHistory(session_id, userId.current, loadedUserType)

      const mapped = (data.history || []).map(m => {
        if (m.role === 'human') {
          return { role: 'user', content: m.content }
        }
        return {
          role: 'bot',
          content: m.content,
          confidence_score: m.confidence_score ?? null,
          citations: m.citations || [],
          guardrail: false,
        }
      })

      sessionId.current = session_id
      setUserType(loadedUserType)
      setMessages(mapped)
    } catch (err) {
      console.error('[loadConversation] failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Renders a precomputed FAQ seed answer instantly, no /query call.
  const sendFaqAnswer = useCallback((question, answer, citations, confidence_score) => {
    setMessages(prev => [
      ...prev,
      { role: 'user', content: question },
      {
        role: 'bot',
        content: answer,
        confidence_score: confidence_score ?? null,
        citations: citations || [],
        guardrail: false,
      },
    ])
  }, [])

  return {
    messages, loading, slowServer, userType,
    send, newConversation, selectMode,
    loadConversation, sendFaqAnswer,
    userId: userId.current,
  }
}