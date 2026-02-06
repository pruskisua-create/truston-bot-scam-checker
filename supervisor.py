#!/usr/bin/env python3
"""
Супервизор для бота Telegram
Автоматически перезапускает бота при падении
"""

import asyncio
import subprocess
import time
import sys
import os
from datetime import datetime


def setup_logging():
    """Настраивает логирование"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y%m%d')}.log")
    return log_file


def run_bot():
    """Запускает основного бота"""
    log_file = setup_logging()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Запуск Telegram бота...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Логи пишутся в: {log_file}")

    try:
        # Запускаем бота с перенаправлением вывода в лог
        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"\n{'=' * 60}\n")
            log.write(f"🚀 Запуск бота: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"{'=' * 60}\n")

            process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=log,
                stderr=log,
                universal_newlines=True,
                bufsize=1
            )

            return process

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 💥 Ошибка при запуске бота: {e}")
        return None


def main():
    """Основная функция супервизора"""
    print(f"{'=' * 60}")
    print("🤖 СУПЕРВИЗОР TRUSTON БОТА")
    print(f"{'=' * 60}")
    print(f"📅 Дата: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print(f"{'=' * 60}")

    restart_count = 0
    max_restarts = 50  # Максимальное количество перезапусков
    restart_delay = 10  # Задержка между перезапусками (секунды)

    while restart_count < max_restarts:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 Попытка #{restart_count + 1}")

            # Запускаем бота
            bot_process = run_bot()

            if bot_process is None:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Не удалось запустить бота")
                restart_count += 1
                time.sleep(restart_delay)
                continue

            # Ждем завершения процесса бота
            while True:
                try:
                    # Проверяем статус процесса
                    return_code = bot_process.poll()

                    if return_code is not None:
                        # Процесс завершился
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Бот завершился с кодом: {return_code}")

                        # Записываем в лог
                        with open(setup_logging(), "a", encoding="utf-8") as log:
                            log.write(f"\n{'=' * 60}\n")
                            log.write(f"⚠️ Бот завершился: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            log.write(f"📊 Код завершения: {return_code}\n")
                            log.write(f"🔄 Перезапуск через {restart_delay} секунд...\n")
                            log.write(f"{'=' * 60}\n")

                        break

                    # Ждем немного перед следующей проверкой
                    time.sleep(5)

                except KeyboardInterrupt:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛑 Получен сигнал остановки...")
                    bot_process.terminate()
                    try:
                        bot_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        bot_process.kill()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 👋 Супервизор остановлен")
                    return

                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ошибка мониторинга: {e}")
                    break

            restart_count += 1

            if restart_count >= max_restarts:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⛔ Достигнут лимит перезапусков ({max_restarts})")
                break

            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Перезапуск через {restart_delay} секунд...")

            # Постепенно увеличиваем задержку при частых падениях
            if restart_count > 5:
                restart_delay = min(restart_delay * 1.5, 300)  # Максимум 5 минут

            time.sleep(restart_delay)

        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛑 Супервизор остановлен пользователем")
            break

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 💥 Критическая ошибка супервизора: {e}")
            restart_count += 1
            time.sleep(restart_delay)

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⛔ Супервизор завершает работу")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Всего перезапусков: {restart_count}")


if __name__ == "__main__":
    main()