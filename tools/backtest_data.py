"""
Tool to generate historical test data for backtesting
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import random
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db_manager
from app.db.models import HistoricalIndexPrice
from app.services.index_service import IndexService
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BacktestDataGenerator:
    """Generate historical test data for backtesting."""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.index_service = IndexService()
    
    async def generate_historical_data(
        self,
        index_id: str,
        start_date: datetime,
        end_date: datetime,
        interval_hours: int = 1,
        base_price: float = 100.0,
        volatility: float = 0.02
    ) -> List[Dict]:
        """
        Generate realistic historical price data for backtesting.
        
        Args:
            index_id: Index identifier
            start_date: Start date for data generation
            end_date: End date for data generation
            interval_hours: Hours between data points
            base_price: Starting price
            volatility: Price volatility (0.0 to 1.0)
        
        Returns:
            List of generated data points
        """
        data_points = []
        current_price = base_price
        current_time = start_date
        
        # Random walk with slight upward trend
        trend = 0.0001  # Small upward trend
        
        while current_time <= end_date:
            # Random walk price change
            change = random.gauss(trend, volatility)
            current_price = max(current_price * (1 + change), 1.0)  # Ensure price stays positive
            
            # Calculate market cap (proportional to price)
            market_cap = current_price * 1000000
            
            # Calculate volume (random but correlated with price movements)
            volume_24h = random.uniform(10000, 100000)
            
            # Price changes
            price_change_24h = random.uniform(-0.05, 0.05)
            price_change_7d = random.uniform(-0.15, 0.15)
            
            data_point = {
                "index_id": index_id,
                "timestamp": current_time,
                "price": round(current_price, 4),
                "market_cap": round(market_cap, 2),
                "volume_24h": round(volume_24h, 2),
                "price_change_24h": round(price_change_24h, 4),
                "price_change_7d": round(price_change_7d, 4),
                "token_count": 3,
                "index_type": "static",
                "calculation_successful": True
            }
            
            data_points.append(data_point)
            
            # Move to next interval
            current_time += timedelta(hours=interval_hours)
        
        return data_points
    
    async def populate_backtest_data(self):
        """Generate and store backtest data for all indexes."""
        logger.info("Starting backtest data generation...")
        
        # Get all indexes
        indexes = await self.index_service.get_all_indexes()
        
        if not indexes:
            logger.warning("No indexes found to generate data for")
            return
        
        # Generate data for the last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        total_records = 0
        
        async with self.db_manager.get_session() as session:
            for index in indexes:
                logger.info(f"Generating backtest data for {index.id}...")
                
                # Generate hourly data points
                data_points = await self.generate_historical_data(
                    index_id=index.id,
                    start_date=start_date,
                    end_date=end_date,
                    interval_hours=1,
                    base_price=index.base_value,
                    volatility=0.02
                )
                
                # Store in database
                for point in data_points:
                    record = HistoricalIndexPrice(**point)
                    session.add(record)
                    total_records += 1
                
                logger.info(f"Generated {len(data_points)} data points for {index.id}")
            
            await session.commit()
        
        logger.info(f"Backtest data generation complete: {total_records} total records")
        return total_records
    
    async def create_test_scenario(
        self,
        scenario_name: str,
        index_id: str,
        data_points: List[Dict]
    ):
        """Create a specific test scenario with predefined data points."""
        logger.info(f"Creating test scenario: {scenario_name}")
        
        async with self.db_manager.get_session() as session:
            for point in data_points:
                point["index_id"] = index_id
                record = HistoricalIndexPrice(**point)
                session.add(record)
            
            await session.commit()
        
        logger.info(f"Test scenario '{scenario_name}' created with {len(data_points)} data points")
    
    async def export_backtest_data(self, output_file: str):
        """Export backtest data to JSON file."""
        logger.info(f"Exporting backtest data to {output_file}...")
        
        async with self.db_manager.get_session() as session:
            stmt = select(HistoricalIndexPrice).order_by(
                HistoricalIndexPrice.index_id,
                HistoricalIndexPrice.timestamp
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            data = []
            for record in records:
                data.append({
                    "index_id": record.index_id,
                    "timestamp": record.timestamp.isoformat(),
                    "price": record.price,
                    "market_cap": record.market_cap,
                    "volume_24h": record.volume_24h,
                    "price_change_24h": record.price_change_24h,
                    "price_change_7d": record.price_change_7d,
                    "token_count": record.token_count,
                    "index_type": record.index_type,
                    "calculation_successful": record.calculation_successful
                })
            
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump({
                    "exported_at": datetime.utcnow().isoformat(),
                    "total_records": len(data),
                    "data": data
                }, f, indent=2)
            
            logger.info(f"Exported {len(data)} records to {output_path}")
            return output_path


async def main():
    """Main entry point for backtest data generation."""
    generator = BacktestDataGenerator()
    
    print("=" * 60)
    print("Backtest Data Generator")
    print("=" * 60)
    print()
    
    # Generate historical data for all indexes
    total_records = await generator.populate_backtest_data()
    
    print(f"\nGenerated {total_records} historical data points")
    
    # Export to JSON file
    output_file = "data/backtest_historical_data.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    export_path = await generator.export_backtest_data(output_file)
    
    print(f"\nBacktest data exported to: {export_path}")
    print("\nYou can use this data to verify API accuracy and backtest changes.")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

