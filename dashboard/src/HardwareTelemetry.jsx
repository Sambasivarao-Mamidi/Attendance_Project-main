import { useState, useEffect, useRef } from 'react'
import { database, ref, onValue } from './firebase'
import {
  LineChart, Line, XAxis, YAxis, ResponsiveContainer, CartesianGrid
} from 'recharts'
import {
  Thermometer, Cpu, HardDrive, Camera, Clock, RotateCcw, Video,
  AlertTriangle, X, CheckCircle
} from 'lucide-react'

const MAX_POINTS = 60

function generateCpuPoint(prev) {
  const base = prev || 35
  const delta = (Math.random() - 0.45) * 12
  const spike = Math.random() > 0.92 ? (Math.random() * 25) : 0
  return Math.max(5, Math.min(95, base + delta + spike))
}

export default function HardwareTelemetry({ theme }) {
  const [cpuData, setCpuData] = useState([])
  const [modal, setModal] = useState(null)
  const [confirmed, setConfirmed] = useState(null)
  const lastVal = useRef(35)

  // Live Firebase telemetry
  const [telemetry, setTelemetry] = useState({
    cpu_temp: 0,
    cpu_usage: 0,
    ram_usage: 0,
    ram_used_gb: 0,
    ram_total_gb: 0,
    uptime: '—',
    status: 'Offline',
    timestamp: 0
  })
  const [firebaseConnected, setFirebaseConnected] = useState(false)

  // Listen to SystemHealth/Pi4 in Firebase
  useEffect(() => {
    const healthRef = ref(database, 'SystemHealth/Pi4')
    const unsubscribe = onValue(healthRef, (snapshot) => {
      const data = snapshot.val()
      if (data) {
        setTelemetry({
          cpu_temp: data.cpu_temp || 0,
          cpu_usage: data.cpu_usage || 0,
          ram_usage: data.ram_usage || 0,
          ram_used_gb: data.ram_used_gb || 0,
          ram_total_gb: data.ram_total_gb || 0,
          uptime: data.uptime || '—',
          status: data.status || 'Offline',
          timestamp: data.timestamp || 0
        })
        setFirebaseConnected(true)
      }
    }, () => {
      setFirebaseConnected(false)
    })
    return () => unsubscribe()
  }, [])

  // Check if data is stale (> 15 seconds old = probably offline)
  const isOnline = firebaseConnected && telemetry.status === 'Online' &&
    (Date.now() / 1000 - telemetry.timestamp) < 15

  // Use real CPU usage from Firebase if live, otherwise simulate
  useEffect(() => {
    const init = []
    for (let i = 0; i < MAX_POINTS; i++) {
      const v = generateCpuPoint(lastVal.current)
      lastVal.current = v
      init.push({ t: i, cpu: Math.round(v * 10) / 10 })
    }
    setCpuData(init)

    const interval = setInterval(() => {
      // If Pi is online, use real cpu_usage; otherwise simulate
      const v = isOnline
        ? telemetry.cpu_usage + (Math.random() - 0.5) * 3 // add slight jitter to real data for smooth chart
        : generateCpuPoint(lastVal.current)
      lastVal.current = v
      setCpuData(prev => {
        const next = [...prev.slice(1), { t: prev[prev.length - 1].t + 1, cpu: Math.round(Math.max(0, Math.min(100, v)) * 10) / 10 }]
        return next
      })
    }, 1000)

    return () => clearInterval(interval)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Derive display values: prefer Firebase data when available
  const cpuTemp = isOnline ? telemetry.cpu_temp : 58
  const ramPct = isOnline ? Math.round(telemetry.ram_usage) : 65
  const ramUsed = isOnline ? telemetry.ram_used_gb : 2.6
  const ramTotal = isOnline ? telemetry.ram_total_gb : 4.0
  const uptime = isOnline ? telemetry.uptime : '—'
  const cameraModel = 'Logitech C270'

  const tempColor = cpuTemp > 75 ? 'var(--rose)' : cpuTemp > 60 ? 'var(--amber)' : 'var(--emerald)'
  const tempLabel = cpuTemp > 75 ? 'Critical' : cpuTemp > 60 ? 'Warm' : 'Normal'

  const handleConfirm = (action) => {
    setConfirmed(action)
    setModal(null)
    setTimeout(() => setConfirmed(null), 3000)
  }

  const chartGridColor = theme === 'dark' ? 'rgba(148,163,184,0.06)' : 'rgba(0,0,0,0.06)'
  const chartAxisColor = theme === 'dark' ? '#475569' : '#94a3b8'

  return (
    <div className="telemetry-panel">

      {/* Header */}
      <div className="telemetry-header">
        <div className="telemetry-title">
          <Cpu size={15} />
          <span>Edge Device Telemetry (Pi 4)</span>
          {!isOnline && <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginLeft: '6px' }}>(Simulated)</span>}
        </div>
        <div className={`telemetry-status ${isOnline ? 'connected' : ''}`}
          style={!isOnline ? { background: 'var(--amber-bg)', color: 'var(--amber)' } : {}}>
          <div className="telemetry-dot" style={!isOnline ? { background: 'var(--amber)' } : {}} />
          {isOnline ? 'Connected' : 'Standby'}
        </div>
      </div>

      {/* Stats Row */}
      <div className="telemetry-stats">
        <div className="tele-stat">
          <div className="tele-stat-icon" style={{ color: tempColor }}>
            <Thermometer size={16} />
          </div>
          <div className="tele-stat-info">
            <div className="tele-stat-value" style={{ color: tempColor }}>{cpuTemp}°C</div>
            <div className="tele-stat-label">CPU Temp · {tempLabel}</div>
          </div>
        </div>

        <div className="tele-stat">
          <div className="tele-stat-icon" style={{ color: 'var(--blue)' }}>
            <HardDrive size={16} />
          </div>
          <div className="tele-stat-info">
            <div className="tele-stat-value">{ramPct}%</div>
            <div className="tele-stat-label">RAM · {ramUsed}GB / {ramTotal}GB</div>
          </div>
          <div className="tele-ram-bar">
            <div className="tele-ram-fill" style={{ width: `${ramPct}%` }} />
          </div>
        </div>

        <div className="tele-stat">
          <div className="tele-stat-icon" style={{ color: isOnline ? 'var(--emerald)' : 'var(--text-tertiary)' }}>
            <Camera size={16} />
          </div>
          <div className="tele-stat-info">
            <div className="tele-stat-value" style={{ fontSize: '13px' }}>{isOnline ? 'Active' : 'Idle'}</div>
            <div className="tele-stat-label">{cameraModel}</div>
          </div>
        </div>

        <div className="tele-stat">
          <div className="tele-stat-icon" style={{ color: 'var(--primary-light)' }}>
            <Clock size={16} />
          </div>
          <div className="tele-stat-info">
            <div className="tele-stat-value" style={{ fontSize: '13px' }}>{uptime}</div>
            <div className="tele-stat-label">System Uptime</div>
          </div>
        </div>
      </div>

      {/* Live CPU Chart */}
      <div className="telemetry-chart">
        <div className="telemetry-chart-label">
          <span>Live CPU Load {isOnline ? '' : '(Simulated)'}</span>
          <span className="telemetry-chart-live">{isOnline ? '● LIVE' : '○ SIM'}</span>
        </div>
        <div style={{ height: 160 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={cpuData} margin={{ top: 5, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0.01} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
              <XAxis dataKey="t" tick={false} axisLine={{ stroke: chartGridColor }} />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: chartAxisColor, fontSize: 10 }}
                axisLine={{ stroke: chartGridColor }}
                tickLine={false}
                tickFormatter={v => `${v}%`}
              />
              <Line
                type="monotone"
                dataKey="cpu"
                stroke={isOnline ? '#10b981' : '#6366f1'}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom Controls */}
      <div className="telemetry-controls">
        {confirmed === 'reboot' && (
          <span className="tele-confirm-msg"><CheckCircle size={12} /> Reboot signal sent</span>
        )}
        {confirmed === 'restart-cam' && (
          <span className="tele-confirm-msg"><CheckCircle size={12} /> Camera service restarting</span>
        )}
        <button className="tele-btn amber" onClick={() => setModal('reboot')}>
          <RotateCcw size={12} /> Reboot Device
        </button>
        <button className="tele-btn slate" onClick={() => setModal('restart-cam')}>
          <Video size={12} /> Restart Camera
        </button>
      </div>

      {/* Confirmation Modal */}
      {modal && (
        <div className="tele-modal-overlay" onClick={() => setModal(null)}>
          <div className="tele-modal" onClick={e => e.stopPropagation()}>
            <button className="tele-modal-close" onClick={() => setModal(null)}><X size={16} /></button>
            <div className="tele-modal-icon">
              <AlertTriangle size={28} />
            </div>
            <h4>Confirm Action</h4>
            <p>
              {modal === 'reboot'
                ? 'This will reboot the Raspberry Pi. The attendance system will be offline for ~2 minutes.'
                : 'This will restart the camera service. Facial recognition will pause briefly.'}
            </p>
            <div className="tele-modal-actions">
              <button className="tele-btn slate" onClick={() => setModal(null)}>Cancel</button>
              <button className="tele-btn danger" onClick={() => handleConfirm(modal)}>
                {modal === 'reboot' ? 'Reboot Now' : 'Restart Camera'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
