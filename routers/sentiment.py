from fastapi import APIRouter, HTTPException, Query, Body, Depends
import os
import database
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import requests
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from datetime import datetime

router = APIRouter()

# Define models for request and response
class SentimentRequest(BaseModel):
    text: str
    coin: str

class SentimentResponse(BaseModel):
    coin: str
    text: str
    sentiment_score: float
    sentiment_label: str
    timestamp: str

# Load sentiment analysis model (lazy loading)
sentiment_model = None
tokenizer = None

def get_sentiment_model():
    global sentiment_model, tokenizer
    if sentiment_model is None or tokenizer is None:
        # Using a pre-trained FinBERT model for financial sentiment analysis
        # This is suitable for crypto news and market sentiment
        model_name = "ProsusAI/finbert"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        sentiment_model = AutoModelForSequenceClassification.from_pretrained(model_name)
    return sentiment_model, tokenizer

def analyze_text_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze the sentiment of text using a pre-trained model
    """
    model, tokenizer = get_sentiment_model()
    
    # Tokenize the text
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
    
    # Get model prediction
    with torch.no_grad():
        outputs = model(**inputs)
        predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
    # FinBERT returns probabilities for [negative, neutral, positive]
    scores = predictions[0].numpy()
    
    # Calculate sentiment score (-1 to 1)
    # -1 is very negative, 0 is neutral, 1 is very positive
    sentiment_score = float(scores[2] - scores[0])  # positive - negative
    
    # Get sentiment label
    if sentiment_score > 0.2:
        sentiment_label = "positive"
    elif sentiment_score < -0.2:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"
    
    return {
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "raw_scores": {
            "negative": float(scores[0]),
            "neutral": float(scores[1]),
            "positive": float(scores[2])
        }
    }

@router.post("/analyze-sentiment", response_model=SentimentResponse)
async def analyze_sentiment(request: SentimentRequest):
    """
    Analyze the sentiment of text for a specific cryptocurrency
    """
    text = request.text
    coin = request.coin.upper()
    
    try:
        # Analyze sentiment
        sentiment_result = analyze_text_sentiment(text)
        
        # Store result in database
        database.store_sentiment(coin, text, sentiment_result["sentiment_score"])
        
        # Prepare response
        response = {
            "coin": coin,
            "text": text,
            "sentiment_score": sentiment_result["sentiment_score"],
            "sentiment_label": sentiment_result["sentiment_label"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing sentiment: {str(e)}")

@router.get("/coin-sentiment/{coin}")
async def get_coin_sentiment(
    coin: str,
    days: int = Query(default=7, description="Number of days of sentiment history to return")
):
    """
    Get sentiment history for a specific cryptocurrency
    """
    coin = coin.upper()
    
    # Get sentiment history from database
    sentiment_history = database.get_sentiment_history(coin, limit=days * 10)  # Approximate, could have multiple per day
    
    if not sentiment_history:
        return {"coin": coin, "sentiment_history": []}
    
    # Format response
    formatted_history = []
    for item in sentiment_history:
        if "_id" in item:
            del item["_id"]
        
        # Add sentiment label if it doesn't exist
        if "sentiment_label" not in item:
            score = item.get("sentiment_score", 0)
            if score > 0.2:
                item["sentiment_label"] = "positive"
            elif score < -0.2:
                item["sentiment_label"] = "negative"
            else:
                item["sentiment_label"] = "neutral"
                
        formatted_history.append(item)
    
    return {
        "coin": coin,
        "sentiment_history": formatted_history
    }

@router.get("/analyze-news-sentiment")
async def analyze_news_sentiment(
    coins: Optional[str] = Query(default="BTC,ETH", description="Comma-separated list of coin symbols"),
    limit: int = Query(default=5, description="Number of news articles to analyze per coin")
):
    """
    Fetch recent news for given coins and analyze their sentiment
    """
    coin_list = [coin.strip().upper() for coin in coins.split(",")]
    results = {}
    
    for coin in coin_list:
        # Get news for this coin
        try:
            response = requests.get(
                f"http://localhost:8000/api/crypto-news?coins={coin}&limit={limit}", 
                timeout=10
            )
            news_data = response.json()
            
            coin_results = []
            
            for article in news_data.get("news", []):
                # Only analyze the title and first part of description to keep it manageable
                text = f"{article.get('title', '')}. {article.get('description', '')[:100]}"
                
                # Analyze sentiment
                sentiment_result = analyze_text_sentiment(text)
                
                # Store in database
                database.store_sentiment(coin, text, sentiment_result["sentiment_score"])
                
                coin_results.append({
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "published_at": article.get("published_at"),
                    "sentiment_score": sentiment_result["sentiment_score"],
                    "sentiment_label": sentiment_result["sentiment_label"]
                })
            
            # Calculate average sentiment
            if coin_results:
                avg_sentiment = sum(item["sentiment_score"] for item in coin_results) / len(coin_results)
                
                results[coin] = {
                    "articles": coin_results,
                    "average_sentiment": avg_sentiment,
                    "overall_sentiment": "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "neutral"
                }
            else:
                results[coin] = {
                    "articles": [],
                    "average_sentiment": 0,
                    "overall_sentiment": "neutral"
                }
                
        except Exception as e:
            results[coin] = {
                "error": f"Failed to analyze news sentiment: {str(e)}",
                "articles": []
            }
    
    return results 