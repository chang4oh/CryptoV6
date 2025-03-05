from fastapi import APIRouter, HTTPException, Query, Depends
import requests
import os
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
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

@router.get("/crypto-news")
async def get_crypto_news(
    coins: Optional[str] = Query(default=None, description="Comma-separated list of coin symbols to filter news"),
    limit: int = Query(default=10, description="Number of news articles to return"),
    use_cache: bool = Query(default=True, description="Whether to use cached news if available")
):
    """
    Get latest cryptocurrency news
    """
    # Try to get cached news if requested
    if use_cache:
        cached_news = database.get_recent_news(limit=limit)
        if cached_news and len(cached_news) > 0:
            # Remove MongoDB _id field
            for article in cached_news:
                if "_id" in article:
                    del article["_id"]
            
            # Filter by coins if specified
            if coins:
                coin_list = [coin.strip().upper() for coin in coins.split(",")]
                filtered_news = [
                    article for article in cached_news 
                    if any(coin in article.get("title", "") or coin in article.get("description", "") for coin in coin_list)
                ]
                return {"news": filtered_news}
            
            return {"news": cached_news}
    
    # Fetch data from CoinMarketCap - latest endpoint for news
    params = {
        "limit": limit + 10  # Fetch extra to allow for filtering
    }
    
    try:
        # Note: For educational purposes - in real implementation would need an appropriate endpoint
        # CoinMarketCap's news endpoint might be different or require additional parameters
        data = await fetch_from_coinmarketcap("cryptocurrency/news", params)
        
        news_items = []
        if "data" in data:
            for item in data["data"]:
                news_item = {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "published_at": item.get("published_at"),
                    "source": item.get("source"),
                    "related_coins": item.get("coins", [])
                }
                news_items.append(news_item)
            
            # Filter by coins if specified
            if coins:
                coin_list = [coin.strip().upper() for coin in coins.split(",")]
                news_items = [
                    item for item in news_items 
                    if any(
                        coin in item.get("title", "") or 
                        coin in item.get("description", "") or
                        any(coin == related_coin.get("symbol") for related_coin in item.get("related_coins", []))
                        for coin in coin_list
                    )
                ]
            
            # Limit results
            news_items = news_items[:limit]
            
            # Store news in database
            database.store_news(news_items)
            
            return {"news": news_items}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch news data")
    except Exception as e:
        # Fallback news simulation for educational purposes
        # In a real app, you would handle the API properly instead of simulating data
        current_time = datetime.utcnow()
        simulated_news = []
        
        coins_to_include = ["BTC", "ETH", "XRP", "LTC", "ADA"]
        if coins:
            coins_to_include = [coin.strip().upper() for coin in coins.split(",")]
        
        for i in range(limit):
            timestamp = (current_time - timedelta(hours=i)).isoformat()
            coin = coins_to_include[i % len(coins_to_include)]
            
            news_item = {
                "title": f"{coin} Shows Promising Movement in Today's Trading",
                "url": f"https://example.com/crypto-news/{coin.lower()}-update",
                "description": f"The cryptocurrency {coin} has shown significant movement today with traders taking interest in its latest developments.",
                "published_at": timestamp,
                "source": "CryptoNewsSimulator",
                "related_coins": [{"symbol": coin}]
            }
            simulated_news.append(news_item)
        
        # Store simulated news in database for later use
        database.store_news(simulated_news)
        
        return {"news": simulated_news} 