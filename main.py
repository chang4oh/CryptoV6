from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Crypto Trading Bot API",
    description="API for cryptocurrency market data, news, sentiment analysis, and trading",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Crypto Trading Bot API. Use /docs to see available endpoints."}

# Import routers after app initialization to avoid circular imports
from routers import market_data, news, sentiment, trading

# Include routers
app.include_router(market_data.router, prefix="/api", tags=["Market Data"])
app.include_router(news.router, prefix="/api", tags=["News"])
app.include_router(sentiment.router, prefix="/api", tags=["Sentiment"])
app.include_router(trading.router, prefix="/api", tags=["Trading"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 