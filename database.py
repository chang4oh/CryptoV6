from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

# Get MongoDB connection string from environment variables
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")

# Connect to MongoDB
client = None

def get_database():
    """
    Returns a database connection.
    Creates a new connection if one doesn't exist.
    """
    global client
    if client is None:
        client = MongoClient(MONGODB_URI)
    return client[DB_NAME]

def get_collection(collection_name):
    """
    Returns a specific collection from the database.
    """
    db = get_database()
    return db[collection_name]

# Collections
MARKET_DATA_COLLECTION = "market_data"
NEWS_COLLECTION = "news"
SENTIMENT_COLLECTION = "sentiment"
TRADES_COLLECTION = "trades"

def store_market_data(data):
    """
    Store market data in MongoDB
    """
    collection = get_collection(MARKET_DATA_COLLECTION)
    data["timestamp"] = datetime.utcnow()
    return collection.insert_one(data)

def get_latest_market_data():
    """
    Get the latest market data from MongoDB
    """
    collection = get_collection(MARKET_DATA_COLLECTION)
    return collection.find_one(sort=[("timestamp", -1)])

def store_news(news_items):
    """
    Store news items in MongoDB
    """
    collection = get_collection(NEWS_COLLECTION)
    for item in news_items:
        item["stored_at"] = datetime.utcnow()
    if isinstance(news_items, list) and len(news_items) > 0:
        return collection.insert_many(news_items)
    return None

def get_recent_news(limit=10):
    """
    Get recent news items from MongoDB
    """
    collection = get_collection(NEWS_COLLECTION)
    return list(collection.find(sort=[("published_at", -1)]).limit(limit))

def store_sentiment(coin, text, score):
    """
    Store sentiment analysis result in MongoDB
    """
    collection = get_collection(SENTIMENT_COLLECTION)
    document = {
        "coin": coin,
        "text": text,
        "sentiment_score": score,
        "timestamp": datetime.utcnow()
    }
    return collection.insert_one(document)

def get_sentiment_history(coin, limit=10):
    """
    Get sentiment history for a specific coin
    """
    collection = get_collection(SENTIMENT_COLLECTION)
    return list(collection.find({"coin": coin}, sort=[("timestamp", -1)]).limit(limit))

def record_trade(user_id, coin, action, amount, price):
    """
    Record a trade in MongoDB
    """
    collection = get_collection(TRADES_COLLECTION)
    trade = {
        "user_id": user_id,
        "coin": coin,
        "action": action,  # "buy" or "sell"
        "amount": amount,
        "price": price,
        "timestamp": datetime.utcnow()
    }
    return collection.insert_one(trade)

def get_trade_history(user_id=None, limit=20):
    """
    Get trade history, optionally filtered by user_id
    """
    collection = get_collection(TRADES_COLLECTION)
    query = {}
    if user_id:
        query["user_id"] = user_id
    return list(collection.find(query, sort=[("timestamp", -1)]).limit(limit)) 