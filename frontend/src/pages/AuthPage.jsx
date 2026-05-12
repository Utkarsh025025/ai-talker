/**
 * Login and Register page — glassmorphism card with animated gradient background.
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Brain, Mail, Lock, User, Eye, EyeOff, ArrowRight, Loader2 } from 'lucide-react'

function InputField({ id, label, icon: Icon, type = 'text', value, onChange, placeholder, error }) {
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-slate-300">{label}</label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
          <Icon size={16} />
        </span>
        <input
          id={id}
          type={isPassword && show ? 'text' : type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="w-full bg-surface-50 border border-white/10 rounded-xl py-3 pl-10 pr-10
                     text-slate-100 placeholder-slate-600 text-sm
                     focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                     transition-all duration-200"
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow(!show)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
          >
            {show ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        )}
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}

export default function AuthPage({ mode = 'login' }) {
  const [isLogin, setIsLogin] = useState(mode === 'login')
  const [form, setForm] = useState({ email: '', username: '', password: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()
  const navigate = useNavigate()

  const handleChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }))
    setErrors((err) => ({ ...err, [field]: '' }))
    setServerError('')
  }

  const validate = () => {
    const errs = {}
    if (!form.email.includes('@')) errs.email = 'Enter a valid email.'
    if (!isLogin && form.username.length < 3) errs.username = 'Username must be at least 3 characters.'
    if (form.password.length < 8) errs.password = 'Password must be at least 8 characters.'
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    setServerError('')
    try {
      if (isLogin) {
        await login(form.email, form.password)
      } else {
        await register(form.email, form.username, form.password)
      }
      navigate('/')
    } catch (err) {
      setServerError(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-surface">
      {/* Animated background blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-brand-700 rounded-full blur-3xl opacity-20 animate-pulse-slow" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-purple-700 rounded-full blur-3xl opacity-20 animate-pulse-slow" style={{ animationDelay: '1.5s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-brand-500 rounded-full blur-3xl opacity-10 animate-pulse-slow" style={{ animationDelay: '0.75s' }} />
      </div>

      <div className="relative z-10 w-full max-w-md px-4">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8 animate-fade-in">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center mb-4 shadow-lg shadow-brand-500/30">
            <Brain className="text-white" size={28} />
          </div>
          <h1 className="text-2xl font-bold gradient-text">AI Talker</h1>
          <p className="text-slate-500 text-sm mt-1">Document & Multimedia Intelligence</p>
        </div>

        {/* Card */}
        <div className="glass p-8 animate-slide-up">
          {/* Tab switcher */}
          <div className="flex mb-6 bg-surface-50 rounded-xl p-1">
            <button
              id="tab-login"
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                isLogin ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              id="tab-register"
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                !isLogin ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign Up
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <InputField
              id="email"
              label="Email"
              icon={Mail}
              type="email"
              value={form.email}
              onChange={handleChange('email')}
              placeholder="you@example.com"
              error={errors.email}
            />
            {!isLogin && (
              <InputField
                id="username"
                label="Username"
                icon={User}
                value={form.username}
                onChange={handleChange('username')}
                placeholder="cooluser42"
                error={errors.username}
              />
            )}
            <InputField
              id="password"
              label="Password"
              icon={Lock}
              type="password"
              value={form.password}
              onChange={handleChange('password')}
              placeholder="••••••••"
              error={errors.password}
            />

            {serverError && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-400">
                {serverError}
              </div>
            )}

            <button
              id="btn-submit-auth"
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-brand-600 to-purple-600 text-white font-semibold
                         py-3 rounded-xl flex items-center justify-center gap-2 mt-2
                         hover:from-brand-500 hover:to-purple-500 transition-all duration-200
                         disabled:opacity-60 disabled:cursor-not-allowed btn-glow"
            >
              {loading ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <>
                  {isLogin ? 'Sign In' : 'Create Account'}
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-slate-600 text-xs mt-4">
          Powered by OpenAI · LangChain · FAISS
        </p>
      </div>
    </div>
  )
}
