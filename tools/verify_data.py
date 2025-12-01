"""
Data verification tool for index data accuracy and consistency
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.index_service import IndexService
from app.services.linkage_finance import LinkageFinanceService
from app.db.database import get_db_manager
from app.db.models import HistoricalIndexPrice
from sqlalchemy import select, and_, func
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataVerifier:
    """Tool for verifying index data accuracy and consistency."""
    
    def __init__(self):
        self.index_service = IndexService()
        self.linkage_service = LinkageFinanceService()
        self.db_manager = get_db_manager()
        self.verification_results = []
    
    async def verify_all_indexes(self) -> Dict:
        """Verify all indexes for data consistency."""
        logger.info("Starting comprehensive data verification...")
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "index_metadata_checks": [],
            "price_calculation_checks": [],
            "historical_data_checks": [],
            "linkage_funds_checks": [],
            "summary": {}
        }
        
        # 1. Check index metadata
        logger.info("Verifying index metadata...")
        metadata_results = await self._verify_index_metadata()
        results["index_metadata_checks"] = metadata_results
        
        # 2. Check price calculations
        logger.info("Verifying price calculations...")
        price_results = await self._verify_price_calculations()
        results["price_calculation_checks"] = price_results
        
        # 3. Check historical data consistency
        logger.info("Verifying historical data...")
        historical_results = await self._verify_historical_data()
        results["historical_data_checks"] = historical_results
        
        # 4. Check Linkage Finance funds
        logger.info("Verifying Linkage Finance funds...")
        linkage_results = await self._verify_linkage_funds()
        results["linkage_funds_checks"] = linkage_results
        
        # Generate summary
        total_checks = len(metadata_results) + len(price_results) + len(historical_results) + len(linkage_results)
        passed_checks = sum(
            len([r for r in results["index_metadata_checks"] if r.get("status") == "pass"]) +
            len([r for r in results["price_calculation_checks"] if r.get("status") == "pass"]) +
            len([r for r in results["historical_data_checks"] if r.get("status") == "pass"]) +
            len([r for r in results["linkage_funds_checks"] if r.get("status") == "pass"])
        )
        
        results["summary"] = {
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": total_checks - passed_checks,
            "success_rate": f"{(passed_checks / total_checks * 100):.1f}%" if total_checks > 0 else "0%"
        }
        
        logger.info(f"Verification complete: {passed_checks}/{total_checks} checks passed")
        
        return results
    
    async def _verify_index_metadata(self) -> List[Dict]:
        """Verify index metadata consistency."""
        results = []
        
        try:
            indexes = await self.index_service.get_all_indexes()
            
            for index in indexes:
                checks = {
                    "index_id": index.id,
                    "checks": []
                }
                
                # Check: Index ID is not empty
                checks["checks"].append({
                    "check": "index_id_not_empty",
                    "status": "pass" if index.id else "fail",
                    "message": "Index ID is present" if index.id else "Index ID is missing"
                })
                
                # Check: Index has valid base value
                checks["checks"].append({
                    "check": "base_value_valid",
                    "status": "pass" if index.base_value > 0 else "fail",
                    "message": f"Base value is {index.base_value}" if index.base_value > 0 else "Base value must be > 0"
                })
                
                # Check: For static indexes, tokens are defined
                if not index.is_dynamic:
                    has_tokens = index.tokens and len(index.tokens) > 0
                    checks["checks"].append({
                        "check": "static_index_has_tokens",
                        "status": "pass" if has_tokens else "fail",
                        "message": f"Index has {len(index.tokens) if index.tokens else 0} tokens" if has_tokens else "Static index must have tokens"
                    })
                    
                    if has_tokens:
                        # Check: Token weights sum to approximately 1.0
                        total_weight = sum(token.weight for token in index.tokens)
                        weight_sum_valid = abs(total_weight - 1.0) < 0.01
                        checks["checks"].append({
                            "check": "token_weights_sum_to_one",
                            "status": "pass" if weight_sum_valid else "fail",
                            "message": f"Token weights sum to {total_weight:.4f}" if weight_sum_valid else f"Token weights sum to {total_weight:.4f}, expected ~1.0"
                        })
                
                # Check: Created and updated dates are valid
                checks["checks"].append({
                    "check": "dates_valid",
                    "status": "pass" if index.created_at <= index.updated_at else "fail",
                    "message": "Dates are valid" if index.created_at <= index.updated_at else "created_at must be <= updated_at"
                })
                
                results.append(checks)
        
        except Exception as e:
            results.append({
                "index_id": "error",
                "checks": [{
                    "check": "metadata_verification",
                    "status": "fail",
                    "message": f"Error verifying metadata: {str(e)}"
                }]
            })
        
        return results
    
    async def _verify_price_calculations(self) -> List[Dict]:
        """Verify price calculation consistency."""
        results = []
        
        try:
            indexes = await self.index_service.get_all_indexes()
            
            for index in indexes:
                try:
                    # Calculate price twice to check consistency
                    price1 = await self.index_service.calculate_index_price(index.id)
                    await asyncio.sleep(0.1)  # Small delay
                    price2 = await self.index_service.calculate_index_price(index.id)
                    
                    # Check: Prices are positive
                    price_valid = price1.price > 0
                    results.append({
                        "index_id": index.id,
                        "check": "price_positive",
                        "status": "pass" if price_valid else "fail",
                        "message": f"Price is {price1.price:.4f}" if price_valid else "Price must be positive"
                    })
                    
                    # Check: Price is consistent (same within small tolerance)
                    price_consistent = abs(price1.price - price2.price) < 0.01
                    results.append({
                        "index_id": index.id,
                        "check": "price_consistent",
                        "status": "pass" if price_consistent else "warn",
                        "message": f"Prices are consistent: {price1.price:.4f} vs {price2.price:.4f}" if price_consistent else f"Price variance detected: {price1.price:.4f} vs {price2.price:.4f}"
                    })
                    
                    # Check: Market cap is valid
                    market_cap_valid = price1.market_cap >= 0
                    results.append({
                        "index_id": index.id,
                        "check": "market_cap_valid",
                        "status": "pass" if market_cap_valid else "fail",
                        "message": f"Market cap is {price1.market_cap:.2f}" if market_cap_valid else "Market cap must be >= 0"
                    })
                
                except Exception as e:
                    results.append({
                        "index_id": index.id,
                        "check": "price_calculation",
                        "status": "fail",
                        "message": f"Failed to calculate price: {str(e)}"
                    })
        
        except Exception as e:
            results.append({
                "index_id": "error",
                "check": "price_verification",
                "status": "fail",
                "message": f"Error verifying prices: {str(e)}"
            })
        
        return results
    
    async def _verify_historical_data(self) -> List[Dict]:
        """Verify historical data consistency."""
        results = []
        
        try:
            indexes = await self.index_service.get_all_indexes()
            
            async with self.db_manager.get_session() as session:
                for index in indexes:
                    # Check: Historical data exists for recent period
                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=7)
                    
                    stmt = select(HistoricalIndexPrice).where(
                        and_(
                            HistoricalIndexPrice.index_id == index.id,
                            HistoricalIndexPrice.timestamp >= start_date,
                            HistoricalIndexPrice.calculation_successful == True
                        )
                    ).order_by(HistoricalIndexPrice.timestamp.desc()).limit(10)
                    
                    result = await session.execute(stmt)
                    records = result.scalars().all()
                    
                    has_recent_data = len(records) > 0
                    results.append({
                        "index_id": index.id,
                        "check": "has_recent_historical_data",
                        "status": "pass" if has_recent_data else "warn",
                        "message": f"Found {len(records)} recent data points" if has_recent_data else "No recent historical data found"
                    })
                    
                    if records:
                        # Check: Historical prices are positive
                        invalid_prices = [r for r in records if r.price <= 0]
                        all_prices_valid = len(invalid_prices) == 0
                        results.append({
                            "index_id": index.id,
                            "check": "historical_prices_positive",
                            "status": "pass" if all_prices_valid else "fail",
                            "message": f"All {len(records)} historical prices are valid" if all_prices_valid else f"{len(invalid_prices)} invalid prices found"
                        })
                        
                        # Check: Historical data is chronologically ordered
                        timestamps = [r.timestamp for r in records]
                        is_ordered = timestamps == sorted(timestamps, reverse=True)
                        results.append({
                            "index_id": index.id,
                            "check": "historical_data_ordered",
                            "status": "pass" if is_ordered else "fail",
                            "message": "Historical data is properly ordered" if is_ordered else "Historical data ordering issue detected"
                        })
        
        except Exception as e:
            results.append({
                "index_id": "error",
                "check": "historical_verification",
                "status": "fail",
                "message": f"Error verifying historical data: {str(e)}"
            })
        
        return results
    
    async def _verify_linkage_funds(self) -> List[Dict]:
        """Verify Linkage Finance funds data."""
        results = []
        
        try:
            funds = await self.linkage_service.get_all_funds()
            
            results.append({
                "check": "funds_count",
                "status": "pass" if len(funds) > 0 else "warn",
                "message": f"Found {len(funds)} Linkage Finance funds" if len(funds) > 0 else "No Linkage Finance funds found"
            })
            
            for fund in funds:
                # Check: Fund has valid ID
                results.append({
                    "fund_id": fund.fund_id,
                    "check": "fund_id_valid",
                    "status": "pass" if fund.fund_id else "fail",
                    "message": "Fund ID is valid" if fund.fund_id else "Fund ID is missing"
                })
                
                # Check: Fund has tokens
                has_tokens = len(fund.tokens) > 0
                results.append({
                    "fund_id": fund.fund_id,
                    "check": "fund_has_tokens",
                    "status": "pass" if has_tokens else "fail",
                    "message": f"Fund has {len(fund.tokens)} tokens" if has_tokens else "Fund must have at least one token"
                })
                
                # Check: Fund factors match tokens
                factors_match = len(fund.tokens) == len(fund.factors)
                results.append({
                    "fund_id": fund.fund_id,
                    "check": "factors_match_tokens",
                    "status": "pass" if factors_match else "fail",
                    "message": f"Fund has {len(fund.factors)} factors for {len(fund.tokens)} tokens" if factors_match else "Token and factor counts don't match"
                })
                
                # Check: Fund can be converted to index
                try:
                    index_metadata = fund.to_index_metadata()
                    results.append({
                        "fund_id": fund.fund_id,
                        "check": "fund_to_index_conversion",
                        "status": "pass",
                        "message": f"Fund successfully converted to index '{index_metadata.id}'"
                    })
                except Exception as e:
                    results.append({
                        "fund_id": fund.fund_id,
                        "check": "fund_to_index_conversion",
                        "status": "fail",
                        "message": f"Failed to convert fund to index: {str(e)}"
                    })
        
        except Exception as e:
            results.append({
                "check": "linkage_funds_verification",
                "status": "fail",
                "message": f"Error verifying Linkage Finance funds: {str(e)}"
            })
        
        return results
    
    def save_report(self, results: Dict, output_path: Optional[str] = None):
        """Save verification report to file."""
        if output_path is None:
            output_path = f"verification_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_file = Path(output_path)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Verification report saved to {output_file}")
        return output_file


async def main():
    """Main entry point for data verification."""
    verifier = DataVerifier()
    
    print("=" * 60)
    print("Cardano Index API - Data Verification Tool")
    print("=" * 60)
    print()
    
    results = await verifier.verify_all_indexes()
    
    # Print summary
    summary = results["summary"]
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']}")
    print("=" * 60)
    
    # Save report
    report_file = verifier.save_report(results)
    print(f"\nFull report saved to: {report_file}")
    
    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

