/**
 * Timestamped topic list for audio/video documents.
 * Each entry has a "Play" button that seeks the media player to that moment.
 */
import { useState, useEffect, useRef } from 'react'
import { Clock, Play, Music2, Video, Loader2, AlertCircle } from 'lucide-react'
import api from '../services/api'

function formatTime(seconds) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function TimestampPanel({ document: doc, onSeek }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeIdx, setActiveIdx] = useState(null)

  const isPDF = doc?.file_type === 'pdf'

  useEffect(() => {
    if (!doc || isPDF) return
    setLoading(true)
    setError('')
    api.get(`/documents/${doc.id}/timestamps`)
      .then(({ data }) => setData(data))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load timestamps.'))
      .finally(() => setLoading(false))
  }, [doc?.id])

  if (!doc) return null
  if (isPDF) return null

  return (
    <div className="glass rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-brand-500/20 flex items-center justify-center">
          <Clock size={14} className="text-brand-400" />
        </div>
        <span className="text-sm font-semibold text-slate-200">Topic Timestamps</span>
        {data?.duration_seconds && (
          <span className="ml-auto text-xs text-slate-500 font-mono">
            {formatTime(data.duration_seconds)} total
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-3 max-h-80 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center gap-2 py-8 text-slate-500">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Extracting topics…</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        {data?.timestamps?.length === 0 && !loading && (
          <p className="text-center text-slate-500 text-sm py-6">No timestamps extracted yet.</p>
        )}

        {data?.timestamps?.map((ts, i) => (
          <button
            key={i}
            id={`timestamp-${i}`}
            onClick={() => {
              setActiveIdx(i)
              onSeek?.(ts.timestamp)
            }}
            className={`w-full flex items-center gap-3 p-3 rounded-xl mb-1 text-left transition-all duration-200
                        ${activeIdx === i
                          ? 'bg-brand-500/20 border border-brand-500/30'
                          : 'hover:bg-white/5 border border-transparent'}`}
          >
            {/* Play button */}
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all
                            ${activeIdx === i
                              ? 'bg-brand-500 text-white shadow-md shadow-brand-500/40'
                              : 'bg-surface-100 text-slate-400 hover:text-brand-400'}`}>
              <Play size={12} className="ml-0.5" />
            </div>

            {/* Timestamp badge */}
            <span className={`font-mono text-xs px-2 py-1 rounded-lg shrink-0
                             ${activeIdx === i ? 'bg-brand-500/30 text-brand-300' : 'bg-surface-100 text-slate-500'}`}>
              {formatTime(ts.timestamp)}
            </span>

            {/* Topic & text */}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-semibold truncate ${activeIdx === i ? 'text-brand-300' : 'text-slate-300'}`}>
                {ts.topic}
              </p>
              <p className="text-xs text-slate-500 truncate">{ts.text}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
