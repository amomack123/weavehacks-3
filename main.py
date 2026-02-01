"""
Pipecat AI Voice Agent - Main Entrypoint

Thin entrypoint that:
1. Validates configuration
2. Creates pipeline
3. Runs the voice agent
"""

import asyncio
import logging
import argparse

from app.config import validate_config, LOGS_DIR, LLM_MODEL, STT_MODEL
from app.pipeline import create_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Pipecat AI Voice Agent"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()


async def main():
    """Main entrypoint"""
    args = parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    
    # Print header
    logger.info("=" * 60)
    logger.info("Pipecat AI Voice Agent")
    logger.info("=" * 60)
    
    # Validate configuration
    try:
        validate_config()
        logger.info("✓ Configuration validated")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Please check your .env file")
        return
    
    # Log configuration
    logger.info(f"Configuration:")
    logger.info(f"  STT Model: {STT_MODEL}")
    logger.info(f"  LLM Model: {LLM_MODEL}")
    logger.info(f"  Logs Directory: {LOGS_DIR.absolute()}")
    logger.info("=" * 60)
    
    # Create pipeline
    try:
        pipeline = create_pipeline()
    except Exception as e:
        logger.error(f"❌ Failed to create pipeline: {e}", exc_info=True)
        return
    
    # Create and start the pipeline using Runner and Task (Pipecat 0.0.101 style)
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask
    
    runner = PipelineRunner()
    task = PipelineTask(pipeline)
    
    logger.info("🚀 Starting pipeline...")
    try:
        await runner.run(task)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Shutting down...")
        logger.info("=" * 60)
        logger.info("Goodbye!")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
