import { Navigate, Route, Routes } from 'react-router-dom'

import { AltarProvider } from './altar/store'
import Bridge from './pages/Bridge'
import Agents from './pages/Agents'
import Atlas from './pages/Atlas'
import Loom from './pages/Loom'
import Nexus from './pages/Nexus'
import Orb from './pages/Orb'
import Applications from './pages/Applications'

export default function App() {
  return (
    <AltarProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/bridge" replace />} />
        <Route path="/bridge" element={<Bridge />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/atlas" element={<Atlas />} />
        <Route path="/loom" element={<Loom />} />
        <Route path="/nexus" element={<Nexus />} />
        <Route path="/orb" element={<Orb />} />
        <Route path="/apps" element={<Applications />} />
        <Route path="*" element={<Navigate to="/bridge" replace />} />
      </Routes>
    </AltarProvider>
  )
}
