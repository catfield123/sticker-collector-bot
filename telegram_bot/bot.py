import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from redis.asyncio import Redis
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=config.bot_token)
dp = Dispatcher()

# Initialize async Redis connection
redis_client: Redis | None = None


# Cache video file_id in memory
cached_video_file_id: str | None = None


async def send_instruction_video(message: Message):
    """Send instruction video using cached file_id or upload new."""
    global cached_video_file_id
    
    # Try to use cached file_id first (fast)
    if cached_video_file_id:
        try:
            await message.answer_video(
                video=cached_video_file_id,
                caption="📖 Инструкция по использованию бота"
            )
            logger.info("Video sent using cached file_id (fast)")
            return
        except Exception as e:
            logger.warning(f"Failed to send video with cached file_id: {e}. Will upload new.")
            cached_video_file_id = None
    
    # Upload video from file (slow, first time or if file_id expired)
    if os.path.exists(config.instruction_video_path):
        try:
            video = FSInputFile(config.instruction_video_path)
            sent_message = await message.answer_video(
                video=video,
                caption="📖 Инструкция по использованию бота"
            )
            
            # Cache file_id for future use
            if sent_message.video:
                cached_video_file_id = sent_message.video.file_id
                logger.info(f"Video uploaded and file_id cached: {cached_video_file_id[:20]}...")
        except Exception as e:
            logger.error(f"Error uploading instruction video: {e}")
            await message.answer("⚠️ Видео с инструкцией временно недоступно.")
    else:
        logger.warning(f"Instruction video not found at: {config.instruction_video_path}")
        await message.answer(
            "⚠️ Видео с инструкцией пока не добавлено.\n"
            "Но бот работает - просто отправь стикер!"
        )


@dp.message(Command('start'))
async def cmd_start(message: Message):
    """Handle /start command - send welcome message and instruction video."""
    welcome_text = (
        "Привет! Это бот для моего мини-проекта, который помогает собирать информацию о стикерпаках!\n\n"
        "Пожалуйста, пришли мне по одному стикеру из каждого добавленного стикерпака, это займёт всего несколько минут! \n\n"
        "Данное действие очень сильно мне поможет, спасибо за помощь! 🙏🙏🙏\n\n"
        "Вот видео пример того, как это делается:"
    )
    
    await message.answer(welcome_text)
    await send_instruction_video(message)


@dp.message(F.sticker)
async def handle_sticker(message: Message):
    """Handle sticker messages - extract sticker pack info and queue for processing."""
    sticker = message.sticker
    
    # Check if sticker belongs to a sticker pack
    if not sticker.set_name:
        await message.answer("⚠️ Этот стикер не принадлежит ни одному стикерпаку.")
        return
    
    try:
        # Get full sticker pack information
        sticker_set = await bot.get_sticker_set(sticker.set_name)
        
        # Prepare data for the queue
        sticker_pack_data = {
            'short_name': sticker_set.name,
            'name': sticker_set.title,
            'sticker_type': sticker_set.sticker_type,
            'link': f"https://t.me/addstickers/{sticker_set.name}",
            'user_id': message.from_user.id
        }
        
        # Add task to queue asynchronously (non-blocking)
        await redis_client.rpush(
            'sticker_processing',
            json.dumps(sticker_pack_data)
        )
        
        logger.info(
            f"Queued sticker pack '{sticker_set.title}', '{sticker_set.name}',  from user {message.from_user.id}"
        )
        
        # Send confirmation to user (now instant!)
        await message.answer(
            "Спасибо! Пришли мне ещё стикеры из других стикерпаков, пожалуйста 🙏"
        )
        
    except Exception as e:
        logger.error(f"Error handling sticker: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке стикера. Пожалуйста, вернитесь позже и попробуйте снова 🙏🙏🙏"
        )


async def main():
    """Main function to start the bot."""
    global redis_client
    
    try:
        logger.info("Starting Telegram bot...")
        logger.info(f"Redis connection: {config.redis_host}:{config.redis_port}")
        
        # Initialize async Redis connection
        redis_client = Redis(
            host=config.redis_host,
            port=config.redis_port,
            decode_responses=False
        )
        
        # Test Redis connection
        await redis_client.ping()
        logger.info("Redis connection successful")
        
        # Start polling with skip_updates=False to process old messages
        await dp.start_polling(
            bot,
            skip_updates=False,  # Process messages that arrived while bot was offline
            allowed_updates=dp.resolve_used_update_types()
        )
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if redis_client:
            await redis_client.close()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
