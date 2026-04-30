import { Outlet, Link } from 'react-router-dom'

export default function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="border-b border-slate-700 px-4 py-3 flex flex-wrap gap-4">
        <Link to="/" className="font-semibold">VoiceApp</Link>
        <Link to="/captures/new" className="text-slate-300 hover:text-white">New Capture</Link>
        <Link to="/captures" className="text-slate-300 hover:text-white">History</Link>
        <Link to="/templates" className="text-slate-300 hover:text-white">Templates</Link>
      </header>
      <main className="p-4 max-w-3xl mx-auto">
        <Outlet />
      </main>
    </div>
  )
}
