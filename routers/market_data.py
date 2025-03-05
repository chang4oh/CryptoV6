from fastapi import APIRouter, HTTPException, Query, Depends
import requests
import os
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
import database

# Load environment variables
load_dotenv()

# Get API key
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

router = APIRouter()

async def fetch_from_coinmarketcap(endpoint: str, params: dict = None) -> Dict:
    """
    Helper function to fetch data from CoinMarketCap API
    """
    base_url = "https://pro-api.coinmarketcap.com/v1"
    url = f"{base_url}/{endpoint}"
    
    headers = {
        "X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY,
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data from CoinMarketCap: {str(e)}")

@router.get("/market-data")
async def get_market_data(
    symbols: str = Query(default="BTC,ETH,XRP,LTC,ADA", description="Comma-separated list of coin symbols"),
    limit: int = Query(default=10, description="Number of results to return"),
    use_cache: bool = Query(default=True, description="Whether to use cached data if available")
):
    """
    Get current market data for the specified cryptocurrencies
    """
    # Try to get cached data if requested
    if use_cache:
        cached_data = database.get_latest_market_data()
        if cached_data:
            # Remove MongoDB _id field
            if "_id" in cached_data:
                del cached_data["_id"]
            return cached_data
    
    # Split the symbols string into a list
    symbol_list = [s.strip() for s in symbols.split(",")]
    
    # Fetch data from CoinMarketCap
    params = {
        "symbol": ",".join(symbol_list),
        "limit": limit,
        "convert": "USD"
    }
    
    data = await fetch_from_coinmarketcap("cryptocurrency/quotes/latest", params)
    
    # Extract the relevant data
    result = {
        "data": {},
        "timestamp": None
    }
    
    if "data" in data:
        for symbol, coin_data in data["data"].items():
            result["data"][symbol] = {
                "name": coin_data["name"],
                "symbol": coin_data["symbol"],
                "price": coin_data["quote"]["USD"]["price"],
                "percent_change_1h": coin_data["quote"]["USD"]["percent_change_1h"],
                "percent_change_24h": coin_data["quote"]["USD"]["percent_change_24h"],
                "percent_change_7d": coin_data["quote"]["USD"]["percent_change_7d"],
                "market_cap": coin_data["quote"]["USD"]["market_cap"],
                "volume_24h": coin_data["quote"]["USD"]["volume_24h"]
            }
    
    # Store data in the database
    database.store_market_data(result)
    
    return result

@router.get("/global-metrics")
async def get_global_metrics():
    """
    Get global cryptocurrency market metrics
    """
    data = await fetch_from_coinmarketcap("global-metrics/quotes/latest")
    
    if "data" in data:
        return {
            "total_market_cap": data["data"]["quote"]["USD"]["total_market_cap"],
            "total_volume_24h": data["data"]["quote"]["USD"]["total_volume_24h"],
            "btc_dominance": data["data"]["btc_dominance"],
            "eth_dominance": data["data"]["eth_dominance"],
            "active_cryptocurrencies": data["data"]["active_cryptocurrencies"],
            "last_updated": data["data"]["last_updated"]
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch global metrics") 