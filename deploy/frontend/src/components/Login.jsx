import { useState } from 'react'
import { Lock, ArrowLeft } from 'lucide-react'
import { login } from '../api/client'

export default function Login({ userType, onSuccess, onBack }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password.trim() || loading) return
    setLoading(true)
    setError('')
    try {
      const data = await login({ user_type: userType, username, password })
      if (data.success) {
        onSuccess(data.token)
      } else {
        setError(data.message)
      }
    } catch (err) {
      setError('Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen flex flex-col items-center justify-center bg-[#0f0f0f]">
      <div className="w-80 flex flex-col gap-4">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <Lock size={16} color="white" />
          </div>
          <span className="text-lg font-semibold text-white capitalize">{userType} Login</span>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            className="px-3 py-2 rounded-lg bg-[#1a1a1a] border border-white/10 text-white/90 text-sm placeholder-white/20 focus:outline-none focus:border-blue-500/50"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="px-3 py-2 rounded-lg bg-[#1a1a1a] border border-white/10 text-white/90 text-sm placeholder-white/20 focus:outline-none focus:border-blue-500/50"
          />

          {error && <div className="text-xs text-red-400">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="mt-1 px-3 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Verifying…' : 'Login'}
          </button>
        </form>

        <button
          onClick={onBack}
          className="flex items-center gap-1 text-xs text-white/30 hover:text-white/60 transition-colors mt-2"
        >
          <ArrowLeft size={12} /> Back to mode select
        </button>
      </div>
    </div>
  )
}