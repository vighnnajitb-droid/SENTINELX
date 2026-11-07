import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, JSON, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SecurityEvent(Base):
    __tablename__ = 'security_events'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=True)
    source_ip = Column(String)
    destination_ip = Column(String)
    event_type = Column(String)
    timestamp = Column(DateTime)
    raw_data = Column(JSONB)
    event_hash = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    incident = relationship("Incident", back_populates="events")

class Incident(Base):
    __tablename__ = 'incidents'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String)
    description = Column(Text)
    status = Column(String, default="open") # open, investigating, resolved, closed
    severity = Column(String, nullable=True) # low, medium, high, critical
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    events = relationship("SecurityEvent", back_populates="incident")
    investigations = relationship("Investigation", back_populates="incident")

class Investigation(Base):
    __tablename__ = 'investigations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey('incidents.id'))
    status = Column(String, default="pending") # pending, running, completed, failed
    summary = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    incident = relationship("Incident", back_populates="investigations")
    agent_runs = relationship("AgentRun", back_populates="investigation")

class AgentRun(Base):
    __tablename__ = 'agent_runs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id = Column(UUID(as_uuid=True), ForeignKey('investigations.id'))
    agent_name = Column(String)
    status = Column(String)
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    investigation = relationship("Investigation", back_populates="agent_runs")

class Approval(Base):
    __tablename__ = 'approvals'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id = Column(UUID(as_uuid=True), ForeignKey('investigations.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    action_type = Column(String)
    status = Column(String, default="pending") # pending, approved, rejected
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    entity_type = Column(String)
    action = Column(String)
    details = Column(JSONB)
    timestamp = Column(DateTime, default=datetime.utcnow)
    previous_hash = Column(String, nullable=True)
    current_hash = Column(String)
