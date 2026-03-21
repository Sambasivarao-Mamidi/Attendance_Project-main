import { useState, useEffect } from 'react'
import { Camera, X, User, Hash, Calendar, Users } from 'lucide-react'
import { database } from './firebase'
import { ref, set } from 'firebase/database'

function EnrollNewStudent() {
  const [isOpen, setIsOpen] = useState(false)
  const [fullName, setFullName] = useState('')
  const [rollNumber, setRollNumber] = useState('')
  const [year, setYear] = useState('')
  const [section, setSection] = useState('')
  const [studentPhone, setStudentPhone] = useState('')
  const [parentPhone, setParentPhone] = useState('')
  const [isCapturing, setIsCapturing] = useState(false)

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  const handleStartCapture = async (e) => {
    e.preventDefault()
    if (!fullName || !rollNumber || !year || !section || !studentPhone || !parentPhone) {
      alert('Please fill in all fields')
      return
    }

    setIsCapturing(true)

    try {
      const commandRef = ref(database, 'Commands/Pi4')
      await set(commandRef, {
        action: 'START_ENROLL',
        student_id: rollNumber,
        student_name: fullName,
        year: year,
        section: section,
        student_phone: studentPhone,
        parent_phone: parentPhone,
        status: 'pending',
        timestamp: Date.now()
      })
      
      alert(`Facial capture started for ${fullName}! Check the Raspberry Pi camera.`)
      setIsOpen(false)
      setFullName('')
      setRollNumber('')
      setYear('')
      setSection('')
      setStudentPhone('')
      setParentPhone('')
    } catch (error) {
      console.error('Error sending command to Firebase:', error)
      alert('Failed to start capture. Please try again.')
    } finally {
      setIsCapturing(false)
    }
  }

  const handleClose = () => {
    setIsOpen(false)
    setFullName('')
    setRollNumber('')
    setYear('')
    setSection('')
    setStudentPhone('')
    setParentPhone('')
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="btn btn-primary"
      >
        <Camera size={14} /> Enroll Student
      </button>

      {isOpen && (
        <div className="modal-overlay" onClick={handleClose}>
          <div 
            className="modal-container" 
            onClick={(e) => e.stopPropagation()}
          >
              <div className="modal-header">
                <div className="modal-title">
                  <Camera size={20} className="modal-camera-icon" />
                  <span>Register New Student</span>
                </div>
                <button className="modal-close" onClick={handleClose}>
                  <X size={20} />
                </button>
              </div>

            <form onSubmit={handleStartCapture}>
              <div className="modal-body">
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label">
                      <User size={14} />
                      Full Name
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="MAMIDI SAMBASIVARAO"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value.toUpperCase())}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      <Hash size={14} />
                      Roll Number
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="22NR1A0462"
                      value={rollNumber}
                      onChange={(e) => setRollNumber(e.target.value.toUpperCase())}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      <Calendar size={14} />
                      Year
                    </label>
                    <select
                      className="form-input form-select"
                      value={year}
                      onChange={(e) => setYear(e.target.value)}
                    >
                      <option value="">Select Year</option>
                      <option value="1">1st Year</option>
                      <option value="2">2nd Year</option>
                      <option value="3">3rd Year</option>
                      <option value="4">4th Year</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      <Users size={14} />
                      Section
                    </label>
                    <select
                      className="form-input form-select"
                      value={section}
                      onChange={(e) => setSection(e.target.value)}
                    >
                      <option value="">Select Section</option>
                      <option value="A">Section A</option>
                      <option value="B">Section B</option>
                      <option value="C">Section C</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      📞 Student Phone
                    </label>
                    <input
                      type="tel"
                      className="form-input"
                      placeholder="10 digit number"
                      maxLength={10}
                      value={studentPhone}
                      onChange={(e) => setStudentPhone(e.target.value.replace(/\D/g, ''))}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      📞 Parent Phone
                    </label>
                    <input
                      type="tel"
                      className="form-input"
                      placeholder="10 digit number"
                      maxLength={10}
                      value={parentPhone}
                      onChange={(e) => setParentPhone(e.target.value.replace(/\D/g, ''))}
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="submit"
                  className={`capture-button ${isCapturing ? 'pulsing' : ''}`}
                  disabled={isCapturing}
                >
                  <Camera size={18} />
                  {isCapturing ? 'Starting Capture...' : 'Start Remote Facial Capture'}
                </button>
                <p className="capture-help">
                  This will wake up the Raspberry Pi camera to capture 20 facial frames.
                </p>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}

export default EnrollNewStudent