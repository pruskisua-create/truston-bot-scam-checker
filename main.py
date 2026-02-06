import asyncio
import os
import sys
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import router


# Настройка логирования
def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y%m%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


async def main():
    logger = setup_logging()

    print("=" * 60)
    print("🤖 ЗАПУСК БОТА TRUSTON")
    print("=" * 60)

    try:
        # Инициализация бота
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()

        # Подключаем роутер
        dp.include_router(router)

        # Проверяем подключение
        me = await bot.get_me()
        logger.info(f"✅ Подключено как: @{me.username}")
        logger.info(f"✅ ID бота: {me.id}")
        logger.info(f"✅ Режим: {'Railway' if 'RAILWAY' in os.environ else 'Локальный ПК'}")

        # Проверяем базу данных
        from database import db
        logger.info(f"✅ База данных: {db.db_path}")

        print("=" * 50)
        print(f"✅ Подключено как: @{me.username}")
        print(f"✅ ID бота: {me.id}")
        print(f"✅ Режим: {'Railway' if 'RAILWAY' in os.environ else 'Локальный ПК'}")
        print(f"✅ База данных: {db.db_path}")
        print("=" * 50)

        # Очищаем старые обновления
        await bot.delete_webhook(drop_pending_updates=True)

        # Запускаем бота
        logger.info("⚡ Бот запущен и слушает сообщения...")
        print("⚡ Бот запущен и слушает сообщения...")
        print("=" * 50)

        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        print(f"💥 Критическая ошибка: {e}")
        print("=" * 50)
        # Ждем перед выходом
        await asyncio.sleep(5)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        sys.exit(1)