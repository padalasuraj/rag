import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from '@/components/ui/Toaster'
import { AppShell } from '@/layouts/AppShell'
import { DashboardPage } from '@/pages/DashboardPage'
import { KnowledgeBasePage } from '@/pages/KnowledgeBasePage'
import { useAppStore } from '@/stores/useAppStore'

export default function App() {
  const fetchHealth = useAppStore((s) => s.fetchHealth)

  useEffect(() => {
    fetchHealth()
  }, [fetchHealth])

  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/app" replace />} />
        <Route element={<AppShell />}>
          <Route path="/app" element={<DashboardPage />} />
          <Route path="/app/kb/:id" element={<KnowledgeBasePage />} />
        </Route>
      </Routes>
      <Toaster />
    </>
  )
}
