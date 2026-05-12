/**
 * Summary panel — fetches and displays the AI-generated summary for a document.
 */
import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { Sparkles, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import api from '../services/api'

export default function SummaryPanel({ document: doc }) {
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [cached, setCached] = useState(false)

  const fetchSummary = async () => {
    if (!doc) return
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get(`/documents/${doc.id}/summary`)
      setSummary(data.summary)
      setCached(data.cached)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate summary.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (doc?.status === 'completed') {
      fetchSummary()
    } else {
      setSummary('')
      setError('')
    }
  }, [doc?.id])

  if (!doc) return null

  return (
    <div className="glass rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-purple-500/20 flex items-center justify-center">
          <Sparkles size={14} className="text-purple-400" />
        </div>
        <span className="text-sm font-semibold text-slate-200">AI Summary</span>
        {cached && (
          <span className="ml-auto text-xs text-slate-600 bg-surface-50 px-2 py-0.5 rounded-full">cached</span>
        )}
        {!loading && summary && (
          <button
            id="btn-refresh-summary"
            onClick={fetchSummary}
            className="ml-auto text-slate-500 hover:text-brand-400 transition-colors"
            title="Regenerate summary"
          >
            <RefreshCw size={13} />
          </button>
        )}
      </div>

      {/* Body */}
      <div className="p-4 max-h-72 overflow-y-auto">
        {loading && (
          <div className="flex items-center gap-2 py-8 justify-center text-slate-500">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Generating summary…</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        {!loading && !error && !summary && doc.status !== 'completed' && (
          <p className="text-center text-slate-500 text-sm py-6">
            {doc.status === 'processing' ? '⏳ Processing document…' : 'Summary will appear once processing is complete.'}
          </p>
        )}

        {summary && !loading && (
          <div className="prose prose-invert prose-sm max-w-none text-slate-300 animate-fade-in">
            <ReactMarkdown>{summary}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
