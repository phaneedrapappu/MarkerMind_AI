"""
Quick test script to verify NSE data fetching works
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_sources.nse_fetcher import NSEDataFetcher


def test_nse_connection():
    """Test NSE data fetching"""
    print("="*60)
    print("  Testing NSE Data Fetcher")
    print("="*60)
    print()
    
    fetcher = NSEDataFetcher()
    
    # Test stocks
    test_stocks = ["TCS", "WIPRO", "DMART"]
    
    for symbol in test_stocks:
        print(f"📊 Fetching data for {symbol}...")
        try:
            data = fetcher.get_stock_quote(symbol)
            if data:
                print(f"✅ SUCCESS: {data['company_name']}")
                print(f"   Price: ₹{data['price']:,.2f}")
                print(f"   Change: {data['change_percent']:+.2f}%")
                print(f"   Volume: {data['volume']:,}")
            else:
                print(f"❌ FAILED: No data received")
        except Exception as e:
            print(f"❌ ERROR: {e}")
        print()
    
    fetcher.close()
    print("="*60)
    print("Test completed!")
    print("="*60)


if __name__ == "__main__":
    test_nse_connection()
