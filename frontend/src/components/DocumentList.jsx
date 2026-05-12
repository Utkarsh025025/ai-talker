/**
 * Document list sidebar — shows uploaded documents with processing status badges.
 */
import { useState, useEffect, useCallback } from 'react'
import {
  FileText, Music, Video, Loader2, CheckCircle2,
  XCircle, Clock, RefreshCw, Trash2,
} from 'lucide-react'
import api from '../services/api'

const STATUS_CONFIG = {
  pending:    { icon: <Clock size={12} />,        label: 'Pending',    color: 'text-amber-400',  bg: 'bg-amber-400/10'  },
  processing: { icon: <Loader2 size={12} className="animate-spin" />, label: 'Processing', color: 'text-blue-400', bg: 'bg-blue-400/10' },
  completed:  { icon: <CheckCircle2 size={12} />, label: 'Ready',      color: 'text-green-400', bg: 'bg-green-400/10' },
  failed:     { icon: <XCircle size={12} />,      label: 'Failed',     color: 'text-red-400',   bg: 'bg-red-400/10'  },
}

function fileTypeIcon(type) {
  if (type === 'pdf') return <FileText size={16} className="text-red-400" />
  if (['mp3', 'wav', 'm4a'].includes(type)) return <Music size={16} className="text-green-400" />
  return <Video size={16} className="text-blue-400" />
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function DocumentList({ selected, onSelect }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState(null)

  const fetchDocs = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/documents/?page=1&page_size=50')
      setDocs(data.items)
    } catch {
      // fail silently — user will see empty list
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => { fetchDocs() }, [])

  // Poll only while documents are actively processing — stop when all done
  useEffect(() => {
    const hasActive = docs.some((d) => ['pending', 'processing'].includes(d.status))
    if (!hasActive) return  // nothing to poll
    const interval = setInterval(fetchDocs, 4000)
    return () => clearInterval(interval)
  }, [docs])

  const deleteDoc = async (e, docId) => {
    e.stopPropagation()
    setDeleting(docId)
    try {
      await api.delete(`/documents/${docId}`)
      setDocs((prev) => prev.filter((d) => d.id !== docId))
      if (selected?.id === docId) onSelect(null)
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
        <h2 className="text-sm font-semibold text-slate-200">My Documents</h2>
        <button
          id="btn-refresh-docs"
          onClick={fetchDocs}
          disabled={loading}
          className="text-slate-500 hover:text-brand-400 transition-colors disabled:opacity-50"
          title="Refresh"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {loading && docs.length === 0 && (
          <div className="flex items-center justify-center gap-2 py-10 text-slate-500">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Loading…</span>
          </div>
        )}

        {!loading && docs.length === 0 && (
          <div className="text-center py-10 text-slate-600">
            <p className="text-sm">No documents yet.</p>
            <p className="text-xs mt-1">Upload a file to get started!</p>
          </div>
        )}

        {docs.map((doc) => {
          const status = STATUS_CONFIG[doc.status] || STATUS_CONFIG.pending
          const isSelected = selected?.id === doc.id

          return (
            <button
              key={doc.id}
              id={`doc-item-${doc.id}`}
              onClick={() => onSelect(doc)}
              className={`w-full flex items-center gap-3 p-3 rounded-xl text-left transition-all duration-200 group
                          ${isSelected
                            ? 'bg-brand-500/20 border border-brand-500/30'
                            : 'border border-transparent hover:bg-white/5'}`}
            >
              {/* File type icon */}
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0
                              ${isSelected ? 'bg-brand-500/30' : 'bg-surface-100'}`}>
                {fileTypeIcon(doc.file_type)}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium truncate ${isSelected ? 'text-brand-200' : 'text-slate-300'}`}>
                  {doc.original_filename}
                </p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`flex items-center gap-0.5 text-xs ${status.color} ${status.bg} px-1.5 py-0.5 rounded-full`}>
                    {status.icon}
                    {status.label}
                  </span>
                  <span className="text-xs text-slate-600">{formatSize(doc.file_size)}</span>
                </div>
              </div>

              {/* Delete */}
              <button
                id={`btn-delete-doc-${doc.id}`}
                onClick={(e) => deleteDoc(e, doc.id)}
                disabled={deleting === doc.id}
                className="opacity-0 group-hover:opacity-100 text-slate-600 hover:text-red-400
                           transition-all shrink-0 disabled:opacity-50"
              >
                {deleting === doc.id
                  ? <Loader2 size={14} className="animate-spin" />
                  : <Trash2 size={14} />
                }
              </button>
            </button>
          )
        })}
      </div>
    </div>
  )
}
