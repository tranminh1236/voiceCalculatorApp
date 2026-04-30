import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Templates from './pages/Templates'
import NewCapture from './pages/NewCapture'
import CaptureDetail from './pages/CaptureDetail'
import History from './pages/History'
import App from './App'
import './styles/globals.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

function Home() {
  return (
    <div className="space-y-2">
      <h1 className="text-2xl font-bold">VoiceApp</h1>
      <p className="text-slate-300">Bộ ghi âm + nhận diện số viết tay.</p>
    </div>
  )
}

function Placeholder({ name }: { name: string }) {
  return <div className="text-slate-300">{name} — TBD</div>
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />}>
            <Route index element={<Home />} />
            <Route path="templates" element={<Templates />} />
            <Route path="captures/new" element={<NewCapture />} />
            <Route path="captures" element={<History />} />
            <Route path="captures/:id" element={<CaptureDetail />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
