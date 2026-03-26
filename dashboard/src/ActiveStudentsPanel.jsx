import { useState, useMemo } from 'react'
import { X, Search, Phone, User, GraduationCap, Hash, Filter } from 'lucide-react'

export default function ActiveStudentsPanel({
  isOpen,
  onClose,
  students,
  studentsConfig,
  onViewStudent
}) {
  const [searchTerm, setSearchTerm] = useState('')
  const [yearFilter, setYearFilter] = useState('all')
  const [sectionFilter, setSectionFilter] = useState('all')

  const uniqueYears = useMemo(() => {
    const years = new Set(students.map(s => s.year).filter(Boolean))
    return Array.from(years).sort()
  }, [students])

  const uniqueSections = useMemo(() => {
    const sections = new Set(students.map(s => s.section).filter(Boolean))
    return Array.from(sections).sort()
  }, [students])

  const filteredStudents = useMemo(() => {
    return students.filter(student => {
      const matchesSearch = searchTerm === '' ||
        student.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        student.rollNo.toLowerCase().includes(searchTerm.toLowerCase())
      
      const matchesYear = yearFilter === 'all' || student.year === yearFilter
      const matchesSection = sectionFilter === 'all' || student.section === sectionFilter
      
      return matchesSearch && matchesYear && matchesSection
    }).sort((a, b) => a.name.localeCompare(b.name))
  }, [students, searchTerm, yearFilter, sectionFilter])

  const getInitials = (name) => {
    return name
      .split(' ')
      .map(w => w[0])
      .join('')
      .slice(0, 2)
      .toUpperCase()
  }

  const config = (rollNo) => studentsConfig?.[rollNo] || {}

  if (!isOpen) return null

  return (
    <>
      <div className="students-panel-overlay" onClick={onClose} />
      <div className="students-panel">
        <div className="students-panel-header">
          <div className="students-panel-title">
            <GraduationCap size={20} />
            <span>Active Students</span>
            <span className="students-count">{filteredStudents.length}</span>
          </div>
          <button className="students-panel-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="students-panel-search">
          <div className="search-input-wrapper">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by name or roll number..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="students-search-input"
            />
          </div>
          
          <div className="students-panel-filters">
            <div className="filter-group">
              <Filter size={14} />
              <select
                value={yearFilter}
                onChange={(e) => setYearFilter(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Years</option>
                {uniqueYears.map(year => (
                  <option key={year} value={year}>Year {year}</option>
                ))}
              </select>
            </div>
            
            <div className="filter-group">
              <select
                value={sectionFilter}
                onChange={(e) => setSectionFilter(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Sections</option>
                {uniqueSections.map(section => (
                  <option key={section} value={section}>Section {section}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="students-panel-list">
          {filteredStudents.length === 0 ? (
            <div className="students-empty">
              <User size={40} />
              <p>No students found</p>
              <span>Try adjusting your search or filters</span>
            </div>
          ) : (
            filteredStudents.map((student) => {
              const studentConfig = config(student.rollNo)
              return (
                <div
                  key={student.rollNo}
                  className="student-card"
                  onClick={() => onViewStudent(student)}
                >
                  <div className="student-card-avatar">
                    {student.profile_picture ? (
                      <img
                        src={student.profile_picture}
                        alt={student.name}
                        className="student-card-photo"
                      />
                    ) : (
                      <div className="student-card-initials">
                        {getInitials(student.name)}
                      </div>
                    )}
                  </div>
                  
                  <div className="student-card-info">
                    <div className="student-card-name">{student.name}</div>
                    <div className="student-card-details">
                      <span className="detail-item">
                        <Hash size={12} />
                        {student.rollNo}
                      </span>
                      <span className="detail-item">
                        <GraduationCap size={12} />
                        Year {student.year || '—'}
                      </span>
                      <span className="detail-item">
                        Section {student.section || '—'}
                      </span>
                    </div>
                    {studentConfig.studentPhone && (
                      <div className="student-card-phone">
                        <Phone size={12} />
                        {studentConfig.studentPhone}
                      </div>
                    )}
                  </div>
                  
                  <div className="student-card-arrow">→</div>
                </div>
              )
            })
          )}
        </div>

        <div className="students-panel-footer">
          Showing {filteredStudents.length} of {students.length} students
        </div>
      </div>
    </>
  )
}
