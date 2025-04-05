from telethon import TelegramClient
import asyncio
from colorama import Fore, Style
import time
import os

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
        self.message_queue.put(("status", self.chat_config["chat_id"], status, color))

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
                message = self.chat_config["messages"][0]  # Берем первое сообщение

                # Определяем порядок отправки
                if voice_enabled and voice_file and voice_first:
                    # Сначала голосовое, потом текст
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
                    
                    await self.update_status(f"Отправка: {message}", Fore.CYAN)
                    await self.client.send_message(self.chat_config["chat_id"], message)
                else:
                    # Сначала текст, потом голосовое
                    await self.update_status(f"Отправка: {message}", Fore.CYAN)
                    await self.client.send_message(self.chat_config["chat_id"], message)
                    
                    if voice_enabled and voice_file and not voice_first:
                        if os.path.exists(voice_file):
                            await asyncio.sleep(self.chat_config["delays"]["between_messages"])
                            await self.update_status(f"Отправка голосового сообщения", Fore.CYAN)
                            try:
                                await self.client.send_file(
                                    self.chat_config["chat_id"],
                                    voice_file,
                                    voice_note=True
                                )
                            except Exception as e:
                                await self.update_status(f"Ошибка отправки голосового: {str(e)}", Fore.RED)

                self.message_count += 1
                self.message_queue.put(("message", self.chat_config["chat_id"], self.message_count))

                # 4. Ждем перед следующим циклом
                await asyncio.sleep(self.chat_config["delays"]["before_cycle"])

            except Exception as e:
                await self.update_status(f"Ошибка: {str(e)}", Fore.RED)
                await asyncio.sleep(self.chat_config["delays"]["error_retry"])

    def stop(self):
        self.is_running = False 