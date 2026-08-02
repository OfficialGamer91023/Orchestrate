"""Run evaluation locally without going through the FastAPI HTTP endpoints."""

import sys
import time
from pathlib import Path

# Add backend to path so we can import app
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.db.database import get_db, create_tables
from app.api.routes.eval import batch_evaluate
from app.core.config import settings

import asyncio

async def main():
    print(f"Starting local evaluation (force_recalculate=True)")
    start = time.time()
    
    # Initialize DB (creates SQLite WAL file if not exists)
    create_tables()
    
    # Get a DB session
    db = next(get_db())
    
    try:
        # Call the endpoint handler directly
        metrics = await batch_evaluate(
            force_recalculate=True,
            db=db,
            _token=settings.API_BEARER_TOKEN,
        )
        
        print("\nEvaluation Complete!")
        print(f"Total Time: {time.time() - start:.1f}s")
        print(f"Total Processed: {metrics.total_processed}")
        print(f"Accuracy: {metrics.accuracy * 100:.1f}%")
        print(f"Macro F1: {metrics.macro_f1 * 100:.1f}%")
        print(f"Notify FPR: {metrics.notify_fpr * 100:.1f}%")
        
        if getattr(metrics, "total_latency_ms", None):
            print(f"Avg Latency: {metrics.avg_latency_ms}ms")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
