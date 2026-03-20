import { useState, useEffect, useMemo } from 'react'
import { database, ref, onValue } from './firebase'
import { Sun, Moon, Download, RefreshCw, Eye } from 'lucide-react'
import StudentProfile from './StudentProfile'
import './App.css'

const COOLDOWN_MS = 90 * 60 * 1000

function App() {
  const [attendanceData, setAttendanceData] = useState([])
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(true)
  const [connectionStatus, setConnectionStatus] = useState('connecting')
  const [lastSync, setLastSync] = useState(null)
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('dashboard-theme') || 'dark'
  })

  // Apply theme to HTML element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('dashboard-theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  // Load attendance data from Firebase
  useEffect(() => {
    setConnectionStatus('connecting')
    const attendanceRef = ref(database, '/attendance')

    const unsubscribe = onValue(attendanceRef, (snapshot) => {
      try {
        const data = snapshot.val()
        if (data) {
          const records = []
          Object.keys(data).forEach(date => {
            const dateRecords = data[date]
            if (typeof dateRecords === 'object') {
              Object.values(dateRecords).forEach(record => {
                if (record && record.name) {
                  records.push({
                    name: record.name,
                    rollNo: record.rollNo || '',
                    year: String(record.year || ''),
                    section: record.section || '',
                    time: record.time || '',
                    date: record.date || date,
                    status: record.status || 'Present'
                  })
                }
              })
            }
          })
          setAttendanceData(records)
          setConnectionStatus('connected')
          setLastSync(new Date())
        } else {
          setAttendanceData([])
          setConnectionStatus('connected')
          setLastSync(new Date())
        }
      } catch (error) {
        console.error('Error parsing Firebase data:', error)
        setConnectionStatus('error')
      } finally {
        setLoading(false)
      }
    }, (error) => {
      console.error('Firebase listener error:', error)
      setConnectionStatus('error')
      setLoading(false)
    })

    return () => unsubscribe()
  }, [])

  // Deduplicate with cooldown
  const deduplicatedData = useMemo(() => {
    const groups = {}
    attendanceData.forEach(record => {
      const key = `${record.rollNo}_${record.date}`
      if (!groups[key]) groups[key] = []
      groups[key].push(record)
    })

    const result = []
    Object.values(groups).forEach(records => {
      records.sort((a, b) => a.time.localeCompare(b.time))
      let lastValidTime = null
      records.forEach(record => {
        const recordTime = new Date(`${record.date}T${record.time}`)
        if (!lastValidTime) {
          result.push(record)
          lastValidTime = recordTime
        } else {
          const timeDiff = recordTime - lastValidTime
          if (timeDiff >= COOLDOWN_MS) {
            result.push(record)
            lastValidTime = recordTime
          }
        }
      })
    })
    return result
  }, [attendanceData])

  const formatDateStr = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const filteredByDate = useMemo(() => {
    const dateStr = formatDateStr(selectedDate)
    return deduplicatedData.filter(record => record.date === dateStr)
  }, [deduplicatedData, selectedDate])

  const filteredData = useMemo(() => {
    if (!searchTerm) return filteredByDate
    const term = searchTerm.toLowerCase()
    return filteredByDate.filter(record =>
      record.name.toLowerCase().includes(term) ||
      record.rollNo.toLowerCase().includes(term)
    )
  }, [filteredByDate, searchTerm])

  const datesWithAttendance = useMemo(() => {
    return new Set(deduplicatedData.map(r => r.date))
  }, [deduplicatedData])

  const uniqueStudents = useMemo(() => {
    return new Set(deduplicatedData.map(r => r.rollNo)).size
  }, [deduplicatedData])

  const stats = useMemo(() => {
    const todayStr = formatDateStr(selectedDate)
    const todayRecords = deduplicatedData.filter(r => r.date === todayStr)
    const uniqueToday = new Set(todayRecords.map(r => r.rollNo)).size
    return {
      total: deduplicatedData.length,
      todayPresent: uniqueToday,
      totalStudents: uniqueStudents,
      sectionA: deduplicatedData.filter(r => r.section === 'A').length,
      sectionB: deduplicatedData.filter(r => r.section === 'B').length,
    }
  }, [deduplicatedData, selectedDate, uniqueStudents])

  const getDaysInMonth = (date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    return { daysInMonth: lastDay.getDate(), startingDay: firstDay.getDay() }
  }

  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
    })
  }

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1))
  }
  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1))
  }
  const selectDay = (day) => {
    if (day) setSelectedDate(new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day))
  }

  const { daysInMonth, startingDay } = getDaysInMonth(currentMonth)
  const today = new Date()
  const selectedDateStr = formatDateStr(selectedDate)

  const exportCSV = () => {
    if (deduplicatedData.length === 0) { alert('No data to export'); return }
    const headers = ['Name', 'Roll No', 'Year', 'Section', 'Date', 'Time', 'Status']
    const rows = deduplicatedData.map(r =>
      [r.name, r.rollNo, r.year, r.section, r.date, r.time, r.status]
    )
    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `attendance_export_${formatDateStr(new Date())}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const statusConfig = {
    connecting: { color: '#f59e0b', text: 'Connecting...', icon: '⏳' },
    connected: { color: '#10b981', text: 'Live', icon: '🟢' },
    error: { color: '#ef4444', text: 'Offline', icon: '🔴' }
  }
  const status = statusConfig[connectionStatus]

  // If a student is selected, show their profile
  if (selectedStudent) {
    return (
      <>
        <div className="bg-gradient" />
        <StudentProfile
          student={selectedStudent}
          records={deduplicatedData}
          onBack={() => setSelectedStudent(null)}
          theme={theme}
        />
      </>
    )
  }

  return (
    <>
      <div className="bg-gradient" />
      <div className="app">
        {/* Header */}
        <header className="header">
          <div className="logo">
            <div className="logo-icon">📋</div>
            <div className="logo-text">
              <h1>Attendance Dashboard</h1>
              <p>Smart Attendance System • Firebase Connected</p>
            </div>
          </div>
          <div className="header-actions">
            <div className="connection-badge" style={{
              background: `${status.color}15`,
              border: `1px solid ${status.color}30`,
              color: status.color,
            }}>
              <span style={{ fontSize: '10px' }}>{status.icon}</span>
              {status.text}
              {lastSync && connectionStatus === 'connected' && (
                <span style={{ opacity: 0.7, fontSize: '11px', marginLeft: '4px' }}>
                  • {lastSync.toLocaleTimeString()}
                </span>
              )}
            </div>
            <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button className="btn btn-glass" onClick={() => window.location.reload()}>
              <RefreshCw size={14} /> Refresh
            </button>
            <button className="btn btn-primary" onClick={exportCSV}>
              <Download size={14} /> Export
            </button>
          </div>
        </header>

        {/* Stats Grid */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon purple">📊</div>
            <div className="stat-value">{stats.total}</div>
            <div className="stat-label">Total Records</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green">✓</div>
            <div className="stat-value">{stats.todayPresent}</div>
            <div className="stat-label">Present on {formatDateStr(selectedDate).slice(5)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon blue">👤</div>
            <div className="stat-value">{stats.totalStudents}</div>
            <div className="stat-label">Total Students</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon pink">👥</div>
            <div className="stat-value">{stats.sectionA}</div>
            <div className="stat-label">Section A</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon orange">👥</div>
            <div className="stat-value">{stats.sectionB}</div>
            <div className="stat-label">Section B</div>
          </div>
        </div>

        {/* Main Content */}
        <div className="main-content">
          {/* Calendar */}
          <div className="calendar-section">
            <div className="calendar-title">📅 Select Date</div>
            <div className="calendar-nav">
              <button onClick={prevMonth}>◀</button>
              <span className="calendar-month">
                {currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
              </span>
              <button onClick={nextMonth}>▶</button>
            </div>
            <div className="calendar-grid">
              {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(d => (
                <div key={d} className="calendar-day-header">{d}</div>
              ))}
              {Array(startingDay).fill(null).map((_, i) => (
                <div key={`empty-${i}`} className="calendar-day empty" />
              ))}
              {Array(daysInMonth).fill(null).map((_, i) => {
                const day = i + 1
                const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
                const isToday = currentMonth.getFullYear() === today.getFullYear() &&
                  currentMonth.getMonth() === today.getMonth() && day === today.getDate()
                const isSelected = dateStr === selectedDateStr
                const hasAttendance = datesWithAttendance.has(dateStr)

                return (
                  <div
                    key={day}
                    className={`calendar-day ${isToday ? 'today' : ''} ${isSelected ? 'selected' : ''} ${hasAttendance ? 'has-attendance' : ''}`}
                    onClick={() => selectDay(day)}
                  >
                    {day}
                  </div>
                )
              })}
            </div>
            <p style={{ marginTop: '12px', fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center' }}>
              Green dots indicate days with attendance
            </p>

            <div className="calendar-info">
              <div className="calendar-info-title">🔥 Firebase Live Data</div>
              {attendanceData.length} raw records loaded<br />
              {deduplicatedData.length} after dedup (90min cooldown)<br />
              {uniqueStudents} unique students tracked
            </div>
          </div>

          {/* Attendance Table */}
          <div className="table-section">
            <div className="table-header">
              <h2>📋 Attendance for {formatDate(selectedDate)}</h2>
              <div className="search-box">
                <input
                  type="text"
                  placeholder="Search by name or roll no..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <span className="record-count">{filteredData.length} records</span>
            </div>
            <div className="table-wrapper">
              {loading ? (
                <div className="loading">
                  <div className="spinner" />
                  <span>Connecting to Firebase...</span>
                </div>
              ) : filteredData.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">📭</div>
                  <h3>No Attendance Records</h3>
                  <p>No attendance found for {formatDate(selectedDate)}</p>
                  <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '6px' }}>
                    Try selecting a date with a green dot on the calendar
                  </p>
                </div>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Student Name</th>
                      <th>Roll Number</th>
                      <th>Year</th>
                      <th>Section</th>
                      <th>Time</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredData.map((record, index) => (
                      <tr key={`${record.rollNo}-${record.date}-${record.time}-${index}`}>
                        <td style={{ color: 'var(--text-tertiary)', fontSize: '12px' }}>{index + 1}</td>
                        <td className="student-name">{record.name}</td>
                        <td><span className="roll-no">{record.rollNo}</span></td>
                        <td>{record.year}</td>
                        <td><span className={`section-badge ${record.section}`}>{record.section}</span></td>
                        <td>{record.time}</td>
                        <td>
                          <span className={`status-badge ${record.status.toLowerCase()}`}>
                            ✓ {record.status}
                          </span>
                        </td>
                        <td>
                          <button
                            className="view-btn"
                            onClick={() => setSelectedStudent(record)}
                          >
                            <Eye size={13} /> View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default App
