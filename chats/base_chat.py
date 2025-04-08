from telethon import TelegramClient
import asyncio
from colorama import Fore, Style
import time
import os
import sys
from telethon import types

class BaseChatWorker:
    def __init__(self, client, chat_config, message_queue):
        self.client = client
        self.chat_config = chat_config
        self.message_queue = message_queue
        self.is_running = True
        self.message_count = 0
        self.status = "Ожидание"
        self.status_color = Fore.YELLOW
        self.bot_username = None  # Will be set by child classes
        self.partner_message = None  # Will be set by child classes

    async def update_status(self, status, color=Fore.YELLOW):
        """Обновляет статус и отправляет его в очередь"""
        self.status = status
        self.status_color = color
        console_msg = f"{color}{self.bot_username}: {status}{Style.RESET_ALL}"
        self.message_queue.put(("status", self.chat_config["chat_id"], console_msg, color))
        self.message_queue.put(("message", self.chat_config["chat_id"], self.message_count))

    async def is_message_from_bot(self, message):
        """Проверяет, что сообщение от нужного бота"""
        try:
            sender = await message.get_sender()
            return sender.username == self.bot_username.replace("@", "")
        except:
            return False

    def get_media_path(self, relative_path):
        """Получает правильный путь к медиафайлу"""
        # Получаем абсолютный путь к директории проекта
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Строим полный путь к файлу
        full_path = os.path.join(project_dir, relative_path)
        # Нормализуем путь для Windows
        return os.path.normpath(full_path)

    async def send_media(self, file_path, voice_note=False, video_note=False):
        """Отправляет медиафайл с правильными атрибутами"""
        try:
            # Получаем правильный путь к файлу
            file_path = self.get_media_path(file_path)
            
            if not os.path.exists(file_path):
                await self.update_status(f"Файл не найден: {file_path}", Fore.RED)
                return False

            # Проверяем размер файла
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                await self.update_status(f"Файл слишком большой: {file_size/1024/1024:.1f}MB", Fore.RED)
                return False

            await self.update_status(f"Отправка медиафайла: {file_path}", Fore.CYAN)

            # Открываем файл в бинарном режиме
            with open(file_path, 'rb') as file:
                # Отправляем файл с правильными атрибутами
                await self.client.send_file(
                    self.chat_config["chat_id"],
                    file,
                    voice_note=voice_note,
                    video_note=video_note,
                    attributes=[
                        types.DocumentAttributeAudio(
                            duration=0,
                            voice=voice_note
                        ) if voice_note else types.DocumentAttributeVideo(
                            duration=0,
                            w=1,
                            h=1,
                            round_message=True
                        )
                    ],
                    force_document=False
                )

            return True
        except Exception as e:
            await self.update_status(f"Ошибка отправки медиа: {str(e)}", Fore.RED)
            return False

    async def run(self):
        """Основной цикл работы чата"""
        while self.is_running:
            try:
                # 1. Отправляем команду для поиска собеседника
                await self.update_status("Отправка команды поиска", Fore.BLUE)
                await self.client.send_message(self.chat_config["chat_id"], "/next")
                await asyncio.sleep(self.chat_config["delays"]["next_command"])

                # 2. Ждем сообщение о найденном собеседнике
                await self.update_status("Ожидание собеседника", Fore.YELLOW)
                partner_found = False
                start_time = time.time()
                
                while time.time() - start_time < self.chat_config["delays"]["message_timeout"]:
                    messages = await self.client.get_messages(self.chat_config["chat_id"], limit=5)
                    for msg in messages:
                        if await self.is_message_from_bot(msg) and msg.text and self.partner_message in msg.text.lower():
                            partner_found = True
                            break
                    if partner_found:
                        break
                    await asyncio.sleep(self.chat_config["delays"]["check_messages"])

                if not partner_found:
                    await self.update_status("Собеседник не найден", Fore.RED)
                    await asyncio.sleep(self.chat_config["delays"]["error_retry"])
                    continue

                # 3. Отправляем сообщение из конфига
                await self.update_status("Собеседник найден", Fore.GREEN)
                await asyncio.sleep(self.chat_config["delays"]["partner_found"])

                message = self.chat_config["messages"][0]
                
                # Отправляем текстовое сообщение
                await self.update_status(f"Отправка: {message}", Fore.CYAN)
                try:
                    await self.client.send_message(self.chat_config["chat_id"], message)
                except Exception as e:
                    await self.update_status(f"Ошибка отправки текста: {str(e)}", Fore.RED)

                # Если включены голосовые сообщения
                if self.chat_config.get("voice_enabled", False):
                    voice_file = self.chat_config.get("voice_file")
                    if voice_file:
                        if await self.send_media(voice_file, voice_note=True):
                            await self.update_status(f"Голосовое сообщение отправлено", Fore.GREEN)

                # Если включены видео-кружки
                if self.chat_config.get("video_note_enabled", False):
                    video_note_file = self.chat_config.get("video_note_file")
                    if video_note_file:
                        if await self.send_media(video_note_file, video_note=True):
                            await self.update_status(f"Видео-кружок отправлен", Fore.GREEN)

                self.message_count += 1
                await self.update_status(f"Отправка завершена", Fore.GREEN)
                try:
                    await asyncio.sleep(self.chat_config["delays"]["between_sessions"])
                except KeyError:
                    await self.update_status("Ошибка в конфигурации задержек", Fore.RED)
                    await asyncio.sleep(10)  # Default delay if "between_sessions" is not set

            except asyncio.CancelledError:
                await self.update_status("Отправка прервана", Fore.YELLOW)
                break
            except Exception as e:
                await self.update_status(f"Ошибка в основном цикле: {str(e)}", Fore.RED)
                try:
                    await asyncio.sleep(self.chat_config["delays"]["error_retry"])
                except KeyError:
                    await self.update_status("Ошибка в конфигурации задержек", Fore.RED)
                    await asyncio.sleep(10)  # Default delay if "error_retry" is not set
