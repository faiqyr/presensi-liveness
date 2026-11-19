import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from contextlib import contextmanager

DATABASE_URL = "sqlite:///./attendance.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    nim = Column(String, unique=True, index=True)
    face_embedding = Column(Text) # Storing as JSON string
    
    attendances = relationship("Attendance", back_populates="student")

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String)

    student = relationship("Student", back_populates="attendances")

def init_db():
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def register_student(nim: str, name: str, embedding: list):
    with get_db() as db:
        # Check if already exists
        existing = db.query(Student).filter(Student.nim == nim).first()
        if existing:
            existing.name = name
            existing.face_embedding = json.dumps(embedding)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_student = Student(
                nim=nim, 
                name=name, 
                face_embedding=json.dumps(embedding)
            )
            db.add(new_student)
            db.commit()
            db.refresh(new_student)
            return new_student

def log_attendance(student_id: int, status: str = "Hadir"):
    with get_db() as db:
        # Check if already logged today to prevent spam (Optional logic, we'll keep it simple for now)
        attendance = Attendance(student_id=student_id, status=status)
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
        return attendance

def get_all_students():
    with get_db() as db:
        return db.query(Student).all()

