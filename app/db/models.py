"""
Database models for historical data storage
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class HistoricalIndexPrice(Base):
    """Model for storing historical index price data."""
    
    __tablename__ = "historical_index_prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    index_id = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    price = Column(Float, nullable=False)
    market_cap = Column(Float, nullable=False, default=0.0)
    volume_24h = Column(Float, nullable=False, default=0.0)
    price_change_24h = Column(Float, nullable=False, default=0.0)
    price_change_7d = Column(Float, nullable=False, default=0.0)
    token_count = Column(Integer, nullable=False, default=0)
    index_type = Column(String(20), nullable=False, default="static")  # static or dynamic
    calculation_successful = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_index_timestamp', 'index_id', 'timestamp'),
        Index('idx_timestamp_index', 'timestamp', 'index_id'),
    )
    
    def __repr__(self):
        return f"<HistoricalIndexPrice(index_id={self.index_id}, timestamp={self.timestamp}, price={self.price})>"

class IndexSnapshot(Base):
    """Model for storing complete index composition snapshots."""
    
    __tablename__ = "index_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    historical_price_id = Column(Integer, nullable=False, index=True)  # Foreign key reference
    index_id = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    token_symbol = Column(String(50), nullable=False)
    token_policy_id = Column(String(200), nullable=False)
    token_name = Column(String(200), nullable=False)
    weight = Column(Float, nullable=False)
    token_price = Column(Float, nullable=False)
    token_market_cap = Column(Float, nullable=False, default=0.0)
    token_volume = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    def __repr__(self):
        return f"<IndexSnapshot(index_id={self.index_id}, token={self.token_symbol}, weight={self.weight})>"

class QuerierStatus(Base):
    """Model for tracking the background querier status."""
    
    __tablename__ = "querier_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    querier_name = Column(String(100), nullable=False, unique=True)
    last_run_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    last_error_message = Column(Text, nullable=True)
    total_runs = Column(Integer, nullable=False, default=0)
    successful_runs = Column(Integer, nullable=False, default=0)
    failed_runs = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<QuerierStatus(name={self.querier_name}, last_run={self.last_run_at})>"
