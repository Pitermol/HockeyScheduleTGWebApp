import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Сюда вставь токен от BotFather
TOKEN = "8961326536:AAH-PhP40fMvTYO1pCvRnIRaYtkWH6h2hEo"

# Сюда вставь HTTPS ссылку на твой index.html
WEBAPP_URL = "https://khhljkmnbh.ru/"

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    # Создаем клавиатуру
    builder = ReplyKeyboardBuilder()
    
    # Добавляем кнопку, которая будет открывать Web App
    builder.button(
        text="📱 Открыть Web App", 
        web_app=WebAppInfo(url=WEBAPP_URL)
    )
    
    # Отправляем сообщение с клавиатурой
    await message.answer(
        "Привет! Нажми на кнопку ниже, чтобы запустить приложение.",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
