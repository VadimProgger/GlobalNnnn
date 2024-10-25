import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_TOKEN = '7789717080:AAFAfRt7TkiYPEPfkMqCqgeA9CFxRWWMgXU'  # Replace with your bot's API token
ADMIN_ID = 1078426356  # Admin ID
GROUP_CHAT_ID = -1002177632005  # Channel ID

bot = Bot(API_TOKEN)
dp = Dispatcher()

news_submissions = {}
user_last_submission_time = {}
user_selection_status = {}

def user_kb():
    kb_list = [
        [KeyboardButton(text="😐Обычный")],
        [KeyboardButton(text="🕶️Анонимный")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)

def admin_kb(user_id):
    kb_list = [
        [InlineKeyboardButton(text="Опубликовать", callback_data=f"publish_{user_id}"),
         InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb_list)

async def notify_admin(user_id, text, media_type, media_id=None):
    message = f"Новая новость от пользователя {user_id}:\n{text}"
    if media_type == 'photo':
        await bot.send_photo(ADMIN_ID, photo=media_id, caption=message, reply_markup=admin_kb(user_id))
    elif media_type == 'video':
        await bot.send_video(ADMIN_ID, video=media_id, caption=message, reply_markup=admin_kb(user_id))
    else:
        await bot.send_message(ADMIN_ID, message, reply_markup=admin_kb(user_id))

@dp.message(CommandStart())
async def start_command(message: types.Message):
    await bot.send_message(chat_id=message.chat.id, text='**👨🏻‍💻Привет!**\n\nСюда можно прислать любую новость: **текст, фото, видео и аудио.**\n\n💁🏻‍♂️Обязательно напишите адрес, место и время, когда это произошло. Ваши фото и видео будут в 10 раз нагляднее, чем просто текст.\n\nПост будет опубликован в канале @GBNEWSo', parse_mode='Markdown')
    await message.answer("⌨️ Выберете тип отправки предложений:", reply_markup=user_kb())
    user_selection_status[message.from_user.id] = None  
    logger.info(f"User {message.from_user.id} started the bot.")

@dp.message()
async def handle_news(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username

    if user_selection_status.get(user_id) is None:
        if message.text == "😐Обычный":
            await message.answer("💁🏻‍♂️ Если есть фото или видео, то прикрепите их к сообщению\n\nРасскажите, что произошло?\n\nПерезапустить бота - команда /start")
            user_selection_status[user_id] = "Обычный"  
            logger.info(f"User {user_id} selected 'Обычный' mode.")
            return  
        elif message.text == "🕶️Анонимный":
            await message.answer("👓 Если есть фото или видео, то прикрепите их к сообщению\n\nРасскажите, что произошло?\n\nПерезапустить бота - команда /start")
            user_selection_status[user_id] = "Анонимный"  
            logger.info(f"User {user_id} selected 'Анонимный' mode.")
            return  
        else:
            await message.answer("❌ Пожалуйста, выберите режим отправки (😐Обычный или 🕶️Анонимный) перед тем, как предлагать новость.")
            return

    current_time = datetime.now()
    last_submission_time = user_last_submission_time.get(user_id)
    if last_submission_time and current_time - last_submission_time < timedelta(seconds=30):
        await message.answer("⏳ Пожалуйста, подождите 30 секунд перед следующей отправкой.")
        return

    user_last_submission_time[user_id] = current_time
    await message.answer("✅ Ваша новость успешно отправлена на проверку!")

    if message.photo:
        caption = message.caption if message.caption else ""
        news_submissions[user_id] = {
            'text': caption,
            'username': user_name,
            'media_type': 'photo',
            'media_id': message.photo[-1].file_id  
        }
        await notify_admin(user_id, caption, 'photo', media_id=message.photo[-1].file_id)
        logger.info(f"User {user_id} submitted a photo news.")
    elif message.video:
        caption = message.caption if message.caption else ""
        news_submissions[user_id] = {
            'text': caption,
            'username': user_name,
            'media_type': 'video',
            'media_id': message.video.file_id  
        }
        await notify_admin(user_id, caption, 'video', media_id=message.video.file_id)
        logger.info(f"User {user_id} submitted a video news.")
    else:
        news_submissions[user_id] = {
            'text': message.text,
            'username': user_name,
            'media_type': None,
            'media_id': None
        }
        await notify_admin(user_id, message.text, 'text')
        logger.info(f"User {user_id} submitted a text news.")

    await message.answer("⌨️ Выберете тип отправки предложений:", reply_markup=user_kb())

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id != ADMIN_ID:
        await callback.answer("Вы не имеете прав для выполнения этой команды.")
        return

    try:
        submitted_user_id = int(callback.data.split('_')[1])
    except IndexError:
        await callback.answer("Ошибка: неверные данные.")
        return

    submission = news_submissions.get(submitted_user_id)
    if callback.data.startswith("publish"):
        await callback.answer("Новость опубликована!")
        if submission:
            if submission['media_type'] == 'photo':
                await bot.send_photo(GROUP_CHAT_ID, photo=submission['media_id'], caption=submission['text'])
            elif submission['media_type'] == 'video':
                await bot.send_video(GROUP_CHAT_ID, video=submission['media_id'], caption=submission['text'])
            else:
                await bot.send_message(GROUP_CHAT_ID, submission['text'])
            news_submissions.pop(submitted_user_id, None) 
            await bot.send_message(submitted_user_id, "📰 Ваша новость была опубликована!")
            await bot.send_message(ADMIN_ID, "Новость успешно опубликована.")
            await callback.message.edit_reply_markup(reply_markup=None)
            logger.info(f"Admin {user_id} published news from user {submitted_user_id}.")
    elif callback.data.startswith("reject"):
        await callback.answer("Новость отклонена!")
        if submission:
            await bot.send_message(submitted_user_id, "❌ Ваша новость была отклонена.")
            news_submissions.pop(submitted_user_id, None)  
        await bot.send_message(ADMIN_ID, "Новость успешно отклонена.")
        await callback.message.edit_reply_markup(reply_markup=None)
        logger.info(f"Admin {user_id} rejected news from user {submitted_user_id}.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
