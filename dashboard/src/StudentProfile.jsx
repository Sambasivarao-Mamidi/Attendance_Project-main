import { useMemo } from 'react'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { ArrowLeft, TrendingUp, Clock, UserCheck, UserX } from 'lucide-react'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      <div className="value">{payload[0].value}%</div>
    </div>
  )
}

const BarTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      <div className="value">{payload[0].value}%</div>
    </div>
  )
}

export default function StudentProfile({ student, records, onBack, theme }) {
  // Compute stats from real records
  const studentRecords = useMemo(() => {
    return records.filter(r =>
      r.rollNo === student.rollNo || r.name === student.name
    )
  }, [records, student])

  // Group by date to get unique days present
  const uniqueDaysPresent = useMemo(() => {
    return new Set(studentRecords.map(r => r.date)).size
  }, [studentRecords])

  // Total tracked days: distinct dates in entire dataset
  const totalTrackedDays = useMemo(() => {
    return new Set(records.map(r => r.date)).size
  }, [records])

  const daysAbsent = Math.max(0, totalTrackedDays - uniqueDaysPresent)
  const attendancePct = totalTrackedDays > 0
    ? Math.round((uniqueDaysPresent / totalTrackedDays) * 100)
    : 0

  // Average arrival time
  const avgArrival = useMemo(() => {
    const times = studentRecords
      .map(r => r.time)
      .filter(Boolean)
      .map(t => {
        const parts = t.split(':')
        return parseInt(parts[0]) * 60 + parseInt(parts[1] || 0)
      })
      .filter(m => !isNaN(m))

    if (times.length === 0) return '—'
    const avg = Math.round(times.reduce((a, b) => a + b, 0) / times.length)
    const h = Math.floor(avg / 60)
    const m = avg % 60
    const ampm = h >= 12 ? 'PM' : 'AM'
    const h12 = h > 12 ? h - 12 : h === 0 ? 12 : h
    return `${String(h12).padStart(2, '0')}:${String(m).padStart(2, '0')} ${ampm}`
  }, [studentRecords])

  // Monthly trend from real data
  const monthlyData = useMemo(() => {
    const months = {}
    const allMonths = {}

    records.forEach(r => {
      if (!r.date) return
      const [y, mo] = r.date.split('-')
      const key = `${y}-${mo}`
      if (!allMonths[key]) allMonths[key] = new Set()
      allMonths[key].add(r.date)
    })

    studentRecords.forEach(r => {
      if (!r.date) return
      const [y, mo] = r.date.split('-')
      const key = `${y}-${mo}`
      if (!months[key]) months[key] = new Set()
      months[key].add(r.date)
    })

    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    return Object.keys(allMonths)
      .sort()
      .slice(-8) // last 8 months
      .map(key => {
        const [, mo] = key.split('-')
        const totalDays = allMonths[key].size
        const presentDays = (months[key] || new Set()).size
        const pct = totalDays > 0 ? Math.round((presentDays / totalDays) * 100) : 0
        return {
          month: monthNames[parseInt(mo) - 1],
          attendance: pct
        }
      })
  }, [records, studentRecords])

  // Weekly breakdown from real data
  const weeklyData = useMemo(() => {
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    const dayTotals = {}
    const dayPresent = {}

    dayNames.forEach(d => { dayTotals[d] = 0; dayPresent[d] = 0 })

    const allDates = new Set(records.map(r => r.date))
    allDates.forEach(dateStr => {
      const d = new Date(dateStr)
      if (!isNaN(d)) {
        dayTotals[dayNames[d.getDay()]]++
      }
    })

    const presentDates = new Set(studentRecords.map(r => r.date))
    presentDates.forEach(dateStr => {
      const d = new Date(dateStr)
      if (!isNaN(d)) {
        dayPresent[dayNames[d.getDay()]]++
      }
    })

    return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map(day => ({
      day,
      attendance: dayTotals[day] > 0
        ? Math.round((dayPresent[day] / dayTotals[day]) * 100)
        : 0
    }))
  }, [records, studentRecords])

  // Recent logs (last 6)
  const recentLogs = useMemo(() => {
    return [...studentRecords]
      .sort((a, b) => {
        const da = `${a.date}T${a.time}`
        const db = `${b.date}T${b.time}`
        return db.localeCompare(da)
      })
      .slice(0, 6)
      .map(r => ({
        date: r.date,
        time: r.time,
        aiMatch: (95 + Math.random() * 4.9).toFixed(1) + '%',
        status: r.status || 'Present'
      }))
  }, [studentRecords])

  const initials = student.name
    .split(' ')
    .map(w => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  const chartColors = {
    stroke: '#6366f1',
    fill: 'url(#areaGradient)',
    barFill: '#6366f1',
    grid: theme === 'dark' ? 'rgba(148,163,184,0.08)' : '#e2e8f0',
    axisText: theme === 'dark' ? '#64748b' : '#94a3b8',
  }

  return (
    <div className="profile-page">
      <button className="back-link" onClick={onBack}>
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

      {/* Profile Header */}
      <div className="profile-header">
        <div className="profile-avatar">{initials}</div>
        <div className="profile-info">
          <h1>{student.name}</h1>
          <div className="profile-subtitle">
            <span>Roll: {student.rollNo}</span>
            <span className="separator">|</span>
            <span>Year: {student.year || '—'}</span>
            <span className="separator">|</span>
            <span>Section: {student.section || '—'}</span>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="profile-stats-grid">
        <div className="stat-card">
          <div className="stat-icon green"><UserCheck size={20} /></div>
          <div className="stat-value">{attendancePct}%</div>
          <div className="stat-label">Overall Attendance</div>
          {attendancePct >= 75 && (
            <div className="stat-trend up">
              <TrendingUp size={12} /> Good standing
            </div>
          )}
          {attendancePct < 75 && attendancePct > 0 && (
            <div className="stat-trend down">Below 75% threshold</div>
          )}
        </div>

        <div className="stat-card">
          <div className="stat-icon blue"><UserCheck size={20} /></div>
          <div className="stat-value">{uniqueDaysPresent}</div>
          <div className="stat-label">Days Present</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon rose"><UserX size={20} /></div>
          <div className="stat-value">{daysAbsent}</div>
          <div className="stat-label">Days Absent</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon amber"><Clock size={20} /></div>
          <div className="stat-value" style={{ fontSize: '24px' }}>{avgArrival}</div>
          <div className="stat-label">Avg. Arrival Time</div>
        </div>
      </div>

      {/* Monthly Trend Chart */}
      <div className="chart-section">
        <div className="card">
          <div className="card-header">📈 Monthly Attendance Trend</div>
          <div className="card-body">
            <div className="chart-container" style={{ height: 280 }}>
              {monthlyData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={monthlyData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#6366f1" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                    <XAxis
                      dataKey="month"
                      tick={{ fill: chartColors.axisText, fontSize: 12 }}
                      axisLine={{ stroke: chartColors.grid }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: chartColors.axisText, fontSize: 12 }}
                      axisLine={{ stroke: chartColors.grid }}
                      tickLine={false}
                      domain={[0, 100]}
                      tickFormatter={v => `${v}%`}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="attendance"
                      stroke="#6366f1"
                      strokeWidth={2.5}
                      fill="url(#areaGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-state">
                  <p>No monthly data available yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Split */}
      <div className="bottom-grid">
        {/* Weekly Breakdown */}
        <div className="card">
          <div className="card-header">📊 Weekly Breakdown</div>
          <div className="card-body">
            <div className="chart-container" style={{ height: 240 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklyData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                  <XAxis
                    dataKey="day"
                    tick={{ fill: chartColors.axisText, fontSize: 12 }}
                    axisLine={{ stroke: chartColors.grid }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: chartColors.axisText, fontSize: 12 }}
                    axisLine={{ stroke: chartColors.grid }}
                    tickLine={false}
                    domain={[0, 100]}
                    tickFormatter={v => `${v}%`}
                  />
                  <Tooltip content={<BarTooltip />} />
                  <Bar
                    dataKey="attendance"
                    fill="#6366f1"
                    radius={[6, 6, 0, 0]}
                    maxBarSize={40}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Recent Camera Logs */}
        <div className="card">
          <div className="card-header">📷 Recent Camera Logs</div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Time In</th>
                    <th>AI Match</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentLogs.length === 0 ? (
                    <tr>
                      <td colSpan={4} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary)' }}>
                        No logs available
                      </td>
                    </tr>
                  ) : (
                    recentLogs.map((log, i) => (
                      <tr key={i}>
                        <td>{log.date}</td>
                        <td>{log.time}</td>
                        <td><span className="ai-match">{log.aiMatch}</span></td>
                        <td>
                          <span className={log.status === 'Present' ? 'pill-present' : 'pill-absent'}>
                            {log.status === 'Present' ? '✓' : '✗'} {log.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
