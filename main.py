
import asyncio
from news_aggregator import main as news_main
from keep_alive import keep_alive

if __name__ == "__main__":
    # Start the keep-alive server
    keep_alive()
    
    # Run the news aggregator
    asyncio.run(news_main())
