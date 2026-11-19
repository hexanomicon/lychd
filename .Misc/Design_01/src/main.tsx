import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'

import './styles.css'
import App from './App'

// Static builds (npm run build:static) use hash URLs so any static host or file path works.
const Router = import.meta.env.MODE === 'static' ? HashRouter : BrowserRouter

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Router>
      <App />
    </Router>
  </React.StrictMode>,
)
