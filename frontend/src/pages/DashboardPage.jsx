/**
 * Main Dashboard page — left sidebar (documents), center (upload + media player + info panels),
 * right panel (chat).
 */
import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Brain, LogOut, Upload, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import DocumentList from '../components/DocumentList'
import DropZone from '../components/DropZone'
import ChatBot from '../components/ChatBot'
import SummaryPanel from '../components/SummaryPanel'
import TimestampPanel from '../components/TimestampPanel'

export default function DashboardPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [showUpload, setShowUpload] = useState(false)
  const [docsKey, setDocsKey] = useState(0)  // bump to refresh DocumentList
  const mediaRef = useRef(null)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleUploaded = () => {
    setShowUpload(false)
    setDocsKey((k) => k + 1)
  }

  // Seek the media player to a timestamp (seconds)
  const handleSeek = (seconds) => {
    if (mediaRef.current) {
      mediaRef.current.currentTime = seconds
      mediaRef.current.play()
    }
  }

  const isAudio = selectedDoc && ['mp3', 'wav', 'm4a'].includes(selectedDoc.file_type)
  const isVideo = selectedDoc?.file_type === 'mp4'

  return (
    <div className="h-screen flex flex-col bg-surface overflow-hidden">
      {/* ── Top Nav ───────────────────────────────────────────────────── */}
      <header className="shrink-0 h-14 border-b border-white/10 flex items-center px-4 gap-4 bg-surface-50/80 backdrop-blur-xl">
        {/* Logo */}
        <div className="flex items-center gap-2 mr-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center">
            <Brain size={16} className="text-white" />
          </div>
          <span className="font-bold gradient-text text-base hidden sm:block">AI Talker</span>
        </div>

        {/* Upload button */}
        <button
          id="btn-toggle-upload"
          onClick={() => setShowUpload(!showUpload)}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 btn-glow
                      ${showUpload
                        ? 'bg-surface-100 border border-white/20 text-slate-300'
                        : 'bg-gradient-to-r from-brand-600 to-purple-600 text-white'}`}
        >
          {showUpload ? <X size={14} /> : <Upload size={14} />}
          {showUpload ? 'Close' : 'Upload'}
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* User & logout */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-400 hidden sm:block">
            {user?.username}
          </span>
          <button
            id="btn-logout"
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-slate-500 hover:text-red-400 text-sm transition-colors"
          >
            <LogOut size={15} />
            <span className="hidden sm:block">Sign out</span>
          </button>
        </div>
      </header>

      {/* ── Upload drawer ─────────────────────────────────────────────── */}
      {showUpload && (
        <div className="shrink-0 border-b border-white/10 bg-surface-50/60 backdrop-blur-xl p-4 animate-slide-up">
          <DropZone onUploaded={handleUploaded} />
        </div>
      )}

      {/* ── Main layout ───────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left: Document list */}
        <aside className="w-64 shrink-0 border-r border-white/10 flex flex-col overflow-hidden bg-surface-50/40">
          <DocumentList key={docsKey} selected={selectedDoc} onSelect={setSelectedDoc} />
        </aside>

        {/* Center: Media player + summary + timestamps */}
        <main className="flex-1 overflow-y-auto p-4 space-y-4">
          {!selectedDoc && (
            <div className="flex flex-col items-center justify-center h-full text-center gap-4 animate-fade-in">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-500/20 to-purple-600/20 flex items-center justify-center border border-brand-500/20">
                <Brain size={36} className="text-brand-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-300 mb-2">Select a document</h2>
                <p className="text-slate-500 text-sm max-w-sm">
                  Choose a document from the sidebar, or upload a new PDF, audio, or video file.
                </p>
              </div>
              <button
                onClick={() => setShowUpload(true)}
                className="px-5 py-2.5 bg-gradient-to-r from-brand-600 to-purple-600 rounded-xl text-white text-sm font-semibold hover:from-brand-500 hover:to-purple-500 transition-all btn-glow"
              >
                Upload your first file
              </button>
            </div>
          )}

          {selectedDoc && (
            <div className="space-y-4 animate-fade-in">
              {/* Doc header */}
              <div className="glass p-4 flex items-center gap-3 rounded-2xl">
                <div className="flex-1 min-w-0">
                  <h2 className="font-semibold text-slate-200 truncate">{selectedDoc.original_filename}</h2>
                  <p className="text-xs text-slate-500 capitalize">{selectedDoc.file_type.toUpperCase()} · {selectedDoc.status}</p>
                </div>
              </div>

              {/* Media player for audio/video */}
              {(isAudio || isVideo) && (
                <div className="glass p-4 rounded-2xl">
                  <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider font-semibold">Media Player</p>
                  {isVideo ? (
                    <video
                      id="media-player"
                      ref={mediaRef}
                      controls
                      className="w-full rounded-xl"
                      src={`/api/documents/${selectedDoc.id}/stream`}
                    />
                  ) : (
                    <audio
                      id="media-player"
                      ref={mediaRef}
                      controls
                      className="w-full"
                      src={`/api/documents/${selectedDoc.id}/stream`}
                    />
                  )}
                </div>
              )}

              {/* Timestamps (audio/video only) */}
              {(isAudio || isVideo) && (
                <TimestampPanel document={selectedDoc} onSeek={handleSeek} />
              )}

              {/* AI Summary */}
              <SummaryPanel document={selectedDoc} />
            </div>
          )}
        </main>

        {/* Right: Chat */}
        <aside className="w-80 xl:w-96 shrink-0 border-l border-white/10 flex flex-col overflow-hidden bg-surface-50/40">
          <ChatBot
            documentId={selectedDoc?.status === 'completed' ? selectedDoc.id : null}
            documentName={selectedDoc?.original_filename}
          />
        </aside>
      </div>
    </div>
  )
}
