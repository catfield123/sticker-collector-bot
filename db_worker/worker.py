import logging
import sys
import time
import json
from redis import Redis
from sqlalchemy.exc import IntegrityError
from config import config

# Add parent directory to path to import shared modules
sys.path.insert(0, '/app')

from shared.database import create_db_engine, init_database, get_session_factory, get_session
from shared.models import StickerPack, UserStickerSubmission

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_sticker_pack(sticker_pack_data: dict):
    """
    Process a sticker pack submission from the queue.
    
    Args:
        sticker_pack_data: Dictionary containing:
            - short_name: Sticker pack short name
            - name: Sticker pack title
            - sticker_type: Type of sticker pack (regular, mask, custom_emoji)
            - link: Link to the sticker pack
            - user_id: Telegram user ID who submitted the sticker
    """
    logger.info(f"Processing sticker pack: {sticker_pack_data['short_name']}")
    
    try:
        # Create engine and session
        engine = create_db_engine()
        session_factory = get_session_factory(engine)
        session = get_session(session_factory)
        
        try:
            # First, try to get or create the sticker pack
            sticker_pack = session.query(StickerPack).filter_by(
                short_name=sticker_pack_data['short_name']
            ).first()
            
            if not sticker_pack:
                # Create new sticker pack
                sticker_pack = StickerPack(
                    short_name=sticker_pack_data['short_name'],
                    name=sticker_pack_data['name'],
                    sticker_type=sticker_pack_data['sticker_type'],
                    link=sticker_pack_data['link']
                )
                session.add(sticker_pack)
                session.flush()  # Get the ID without committing
                logger.info(f"Created new sticker pack: {sticker_pack.name} (ID: {sticker_pack.id})")
            else:
                logger.info(f"Sticker pack already exists: {sticker_pack.name} (ID: {sticker_pack.id})")
            
            # Now create or update user submission
            submission = session.query(UserStickerSubmission).filter_by(
                user_id=sticker_pack_data['user_id'],
                sticker_pack_id=sticker_pack.id
            ).first()
            
            if not submission:
                # Create new submission
                submission = UserStickerSubmission(
                    user_id=sticker_pack_data['user_id'],
                    sticker_pack_id=sticker_pack.id
                )
                session.add(submission)
                logger.info(
                    f"Recorded submission from user {sticker_pack_data['user_id']} "
                    f"for sticker pack {sticker_pack.name}"
                )
            else:
                logger.info(
                    f"User {sticker_pack_data['user_id']} already submitted "
                    f"sticker pack {sticker_pack.name}"
                )
            
            # Commit transaction
            session.commit()
            logger.info("Successfully processed sticker pack submission")
            
        except IntegrityError as e:
            session.rollback()
            logger.warning(f"Integrity error (likely duplicate): {e}")
            # This is expected for duplicate submissions, not an error
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing sticker pack: {e}", exc_info=True)
            raise
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Fatal error in process_sticker_pack: {e}", exc_info=True)
        raise


def wait_for_redis(redis_conn, max_attempts=30, delay=2):
    """Wait for Redis to become available."""
    for attempt in range(max_attempts):
        try:
            redis_conn.ping()
            logger.info("Redis connection successful")
            return True
        except Exception as e:
            logger.warning(f"Waiting for Redis... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(delay)
    
    logger.error("Failed to connect to Redis")
    return False


def wait_for_postgres(max_attempts=30, delay=2):
    """Wait for PostgreSQL to become available and initialize database."""
    for attempt in range(max_attempts):
        try:
            engine = create_db_engine()
            # Try to connect
            connection = engine.connect()
            connection.close()
            
            # Initialize database tables
            init_database(engine)
            logger.info("PostgreSQL connection successful and database initialized")
            return True
        except Exception as e:
            logger.warning(
                f"Waiting for PostgreSQL... (attempt {attempt + 1}/{max_attempts}): {e}"
            )
            time.sleep(delay)
    
    logger.error("Failed to connect to PostgreSQL")
    return False


def main():
    """Main function to start the worker."""
    try:
        logger.info("Starting DB Worker...")
        logger.info(f"Redis: {config.redis_host}:{config.redis_port}")
        logger.info(f"PostgreSQL: {config.postgres_host}:{config.postgres_port}/{config.postgres_db}")
        
        # Wait for PostgreSQL
        if not wait_for_postgres():
            logger.error("PostgreSQL is not available. Exiting.")
            sys.exit(1)
        
        # Connect to Redis
        redis_conn = Redis(
            host=config.redis_host,
            port=config.redis_port,
            decode_responses=True  # Enable string decoding for JSON
        )
        
        # Wait for Redis
        if not wait_for_redis(redis_conn):
            logger.error("Redis is not available. Exiting.")
            sys.exit(1)
        
        logger.info("Worker ready. Listening to queue: sticker_processing")
        
        # Process tasks from Redis list
        while True:
            try:
                # Blocking pop with timeout (waits for new items)
                result = redis_conn.blpop('sticker_processing', timeout=5)
                
                if result:
                    _, message_data = result
                    sticker_pack_data = json.loads(message_data)
                    
                    logger.info(f"Processing task: {sticker_pack_data['short_name']}")
                    process_sticker_pack(sticker_pack_data)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {e}")
            except Exception as e:
                logger.error(f"Error processing task: {e}", exc_info=True)
                # Continue processing other tasks
                time.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
