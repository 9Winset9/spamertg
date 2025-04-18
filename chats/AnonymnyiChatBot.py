from telethon import TelegramClient
import asyncio
from colorama import Fore, Style
import time
import os
from telethon import types
from utils.logger import logger

class AnonymnyiChatBotWorker:
    def __init__(self, client, chat_config, message_queue):
        self.client = client
        self.chat_config = chat_config
        self.message_queue = message_queue
        self.is_running = True
        self.message_count = 0
        self.status = "Ожидание"
        self.status_color = Fore.YELLOW
        self.bot_username = "@Anonymnyi_chat_bot"

    async def update_status(self, status, color=Fore.YELLOW):
        self.status = status
        self.status_color = color
        console_msg = logger.log(self.bot_username, status, color)
        self.message_queue.put(("status", self.chat_config["chat_id"], console_msg, color))
        self.message_queue.put(("message", self.chat_config["chat_id"], self.message_count))

    async def is_message_from_bot(self, message):
        """Проверяет, что сообщение от нужного бота"""
        try:
            sender = await message.get_sender()
            return sender.username == self.bot_username.replace("@", "")
        except:
            return False

    async def send_media(self, file_path, voice_note=False, video_note=False):
        try:
            if voice_note:
                await self.client.send_file(
                    self.chat_config["chat_id"],
                    file_path,
                    voice_note=True,
                    attributes=[types.DocumentAttributeAudio(
                        duration=0,  # Длительность определится автоматически
                        voice=True
                    )]
                )
            elif video_note:
                await self.client.send_file(
                    self.chat_config["chat_id"],
                    file_path,
                    video_note=True,
                    attributes=[types.DocumentAttributeVideo(
                        duration=0,
                        w=1,
                        h=1,
                        round_message=True
                    )]
                )
            return True
        except Exception as e:
            await self.update_status(f"Ошибка отправки медиа: {str(e)}", Fore.RED)
            return False

    async def run(self):
        while self.is_running:
            try:
                # 1. Отправляем команду для поиска собеседника
                await self.update_status("Отправка /next", Fore.BLUE)
                await self.client.send_message(self.chat_config["chat_id"], "/next")
                await asyncio.sleep(self.chat_config["delays"]["next_command"])

                # 2. Ждем сообщение о найденном собеседнике
                await self.update_status("Ожидание собеседника", Fore.YELLOW)
                partner_found = False
                start_time = time.time()
                
                while time.time() - start_time < self.chat_config["delays"]["message_timeout"]:
                    messages = await self.client.get_messages(self.chat_config["chat_id"], limit=5)
                    for msg in messages:
                        if await self.is_message_from_bot(msg) and msg.text and "собеседник найден" in msg.text.lower():
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
