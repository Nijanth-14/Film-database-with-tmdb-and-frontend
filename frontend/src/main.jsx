import React from 'react'
import ReactDOM from 'react-dom/client'
import { MotionConfig } from 'framer-motion'
import Auth from './Auth.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <MotionConfig reducedMotion="user" transition={{ type: 'spring', stiffness: 320, damping: 30, mass: 0.85 }}><Auth /></MotionConfig>
  </React.StrictMode>,
)
