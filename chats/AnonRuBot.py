from telethon import TelegramClient
import asyncio
from colorama import Fore, Style
import time
import os
from telethon import types
from utils.logger import logger

class AnonRuBotWorker:
    def __init__(self, client, chat_config, message_queue):
        self.client = client
        self.chat_config = chat_config
        self.message_queue = message_queue
        self.is_running = True
        self.message_count = 0
        self.status = "Ожидание"
        self.status_color = Fore.YELLOW
        self.bot_username = "@AnonRuBot"

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

    async def run(self):
        while self.is_running:
            try:
                # 1. Отправляем /next
                await self.update_status("Отправка /next", Fore.BLUE)
                await self.client.send_message(self.chat_config["chat_id"], "/next")
                await asyncio.sleep(self.chat_config["delays"]["next_command"])

                # 2. Ждем сообщение "собеседник найден" только от бота
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

                voice_enabled = self.chat_config.get("voice_enabled", False)
                voice_file = self.chat_config.get("voice_file")
                voice_first = self.chat_config.get("voice_first", True)
                
                video_note_enabled = self.chat_config.get("video_note_enabled", False)
                video_note_file = self.chat_config.get("video_note_file")
                video_note_first = self.chat_config.get("video_note_first", True)
                
                message = self.chat_config["messages"][0]

                # Определяем порядок отправки
                if voice_enabled and voice_file and voice_first:
                    if os.path.exists(voice_file):
                        await self.update_status(f"Отправка голосового сообщения", Fore.CYAN)
                        try:
                            await self.client.send_file(
                                self.chat_config["chat_id"],
                                voice_file,
                                voice_note=True
                            )
                            await asyncio.sleep(self.chat_config["delays"]["between_messages"])
                        except Exception as e:
                            await self.update_status(f"Ошибка отправки голосового: {str(e)}", Fore.RED)
                
                elif video_note_enabled and video_note_file and video_note_first:
                    if os.path.exists(video_note_file):
                        await self.update_status(f"Отправка видео-кружка", Fore.CYAN)
                        try:
                            with open(video_note_file, 'rb') as video_file:
                                await self.client.send_file(
                                    self.chat_config["chat_id"],
                                    video_file,
                                    video_note=True
                                )
                            await asyncio.sleep(self.chat_config["delays"]["between_messages"])
                        except Exception as e:
                            await self.update_status(f"Ошибка отправки видео-кружка: {str(e)}", Fore.RED)

                # Отправляем текстовое сообщение
                await self.update_status(f"Отправка: {message}", Fore.CYAN)
                try:
                    await self.client.send_message(self.chat_config["chat_id"], message)
                    await asyncio.sleep(self.chat_config["delays"]["between_messages"])
                except Exception as e:
                    await self.update_status(f"Ошибка отправки текста: {str(e)}", Fore.RED)

                # Отправляем оставшиеся голосовые сообщения
                if voice_enabled and voice_file and not voice_first:
                    if os.path.exists(voice_file):
                        await self.update_status(f"Отправка голосового сообщения", Fore.CYAN)
                        try:
                            await self.client.send_file(
                                self.chat_config["chat_id"],
                                voice_file,
                                voice_note=True
                            )
                        except Exception as e:
                            await self.update_status(f"Ошибка отправки голосового: {str(e)}", Fore.RED)

                # Отправляем оставшиеся видео-кружки
                elif video_note_enabled and video_note_file and not video_note_first:
                    if os.path.exists(video_note_file):
                        await self.update_status(f"Отправка видео-кружка", Fore.CYAN)
                        try:
                            with open(video_note_file, 'rb') as video_file:
                                await self.client.send_file(
                                    self.chat_config["chat_id"],
                                    video_file,
                                    video_note=True
                                )
                        except Exception as e:
                            await self.update_status(f"Ошибка отправки видео-кружка: {str(e)}", Fore.RED)

                self.message_count += 1
                await self.update_status(f"Отправка: {message}", Fore.GREEN)
                try:
                    await asyncio.sleep(self.chat_config["delays"]["between_sessions"])
                except KeyError:
                    await self.update_status("Ошибка в конфигурации задержек", Fore.RED)
                    await asyncio.sleep(10)  # Default delay if "between_sessions" is not set

            except Exception as e:
                await self.update_status(f"Ошибка в основном цикле: {str(e)}", Fore.RED)
                try:
                    await asyncio.sleep(self.chat_config["delays"]["error_retry"])
                except KeyError:
                    await self.update_status("Ошибка в конфигурации задержек", Fore.RED)
                    await asyncio.sleep(10)  # Default delay if "error_retry" is not set

    def stop(self):
        self.is_running = False