/**
 * Drag-and-drop file upload zone.
 * Accepts PDF, MP3, MP4, WAV files with visual feedback.
 */
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Music, Video, X, Loader2, CheckCircle2 } from 'lucide-react'
import api from '../services/api'

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'audio/mpeg': ['.mp3'],
  'audio/wav': ['.wav'],
  'audio/x-wav': ['.wav'],
  'audio/mp4': ['.m4a'],
  'video/mp4': ['.mp4'],
}

function fileIcon(type) {
  if (type?.includes('pdf')) return <FileText size={20} className="text-red-400" />
  if (type?.includes('audio') || type?.includes('mpeg')) return <Music size={20} className="text-green-400" />
  return <Video size={20} className="text-blue-400" />
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function DropZone({ onUploaded }) {
  const [files, setFiles] = useState([])  // { file, status: 'idle'|'uploading'|'done'|'error', message }

  const onDrop = useCallback((accepted) => {
    const newFiles = accepted.map((f) => ({ file: f, status: 'idle', message: '' }))
    setFiles((prev) => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: 100 * 1024 * 1024,
    multiple: true,
  })

  const uploadFile = async (index) => {
    setFiles((prev) =>
      prev.map((f, i) => (i === index ? { ...f, status: 'uploading' } : f))
    )
    const { file } = files[index]
    const fd = new FormData()
    fd.append('file', file)
    try {
      const { data } = await api.post('/documents/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setFiles((prev) =>
        prev.map((f, i) =>
          i === index ? { ...f, status: 'done', message: `ID: ${data.id}`, documentId: data.id } : f
        )
      )
      onUploaded?.(data)
    } catch (err) {
      setFiles((prev) =>
        prev.map((f, i) =>
          i === index
            ? { ...f, status: 'error', message: err.response?.data?.detail || 'Upload failed' }
            : f
        )
      )
    }
  }

  const uploadAll = () => {
    files.forEach((f, i) => {
      if (f.status === 'idle') uploadFile(i)
    })
  }

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-4">
      {/* Drop target */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed border-white/20 rounded-2xl p-10 text-center cursor-pointer
                    transition-all duration-300 hover:border-brand-500/50 hover:bg-brand-500/5
                    ${isDragActive ? 'drop-active' : ''}`}
      >
        <input {...getInputProps()} id="file-drop-input" />
        <div className="flex flex-col items-center gap-3">
          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300
                          ${isDragActive
                            ? 'bg-brand-500/30 shadow-lg shadow-brand-500/30'
                            : 'bg-surface-50'}`}>
            <Upload size={28} className={isDragActive ? 'text-brand-400' : 'text-slate-500'} />
          </div>
          {isDragActive ? (
            <p className="text-brand-400 font-semibold">Drop files here!</p>
          ) : (
            <>
              <p className="text-slate-300 font-semibold">Drag & drop files here</p>
              <p className="text-slate-500 text-sm">or click to browse</p>
            </>
          )}
          <div className="flex gap-2 mt-1">
            {['.pdf', '.mp3', '.mp4', '.wav'].map((ext) => (
              <span key={ext} className="px-2.5 py-1 bg-surface-100 rounded-full text-xs text-slate-400 font-mono">
                {ext}
              </span>
            ))}
          </div>
          <p className="text-slate-600 text-xs">Max 100 MB per file</p>
        </div>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((item, i) => (
            <div key={i} className="glass p-4 flex items-center gap-3 rounded-xl">
              {fileIcon(item.file.type)}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-200 font-medium truncate">{item.file.name}</p>
                <p className="text-xs text-slate-500">
                  {formatSize(item.file.size)}
                  {item.message && (
                    <span className={`ml-2 ${item.status === 'error' ? 'text-red-400' : 'text-green-400'}`}>
                      · {item.message}
                    </span>
                  )}
                </p>
              </div>

              {/* Status indicator */}
              {item.status === 'uploading' && <Loader2 size={18} className="text-brand-400 animate-spin shrink-0" />}
              {item.status === 'done' && <CheckCircle2 size={18} className="text-green-400 shrink-0" />}
              {item.status === 'error' && (
                <span className="text-xs text-red-400 shrink-0">Failed</span>
              )}
              {(item.status === 'idle' || item.status === 'error') && (
                <button
                  onClick={() => removeFile(i)}
                  id={`remove-file-${i}`}
                  className="text-slate-600 hover:text-red-400 transition-colors shrink-0"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          ))}

          {/* Upload all button */}
          {files.some((f) => f.status === 'idle') && (
            <button
              id="btn-upload-all"
              onClick={uploadAll}
              className="w-full py-3 bg-gradient-to-r from-brand-600 to-purple-600 rounded-xl
                         text-white font-semibold text-sm hover:from-brand-500 hover:to-purple-500
                         transition-all duration-200 flex items-center justify-center gap-2 btn-glow"
            >
              <Upload size={16} />
              Upload {files.filter((f) => f.status === 'idle').length} file(s)
            </button>
          )}
        </div>
      )}
    </div>
  )
}
