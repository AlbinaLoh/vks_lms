import os
import django
import sys
from asgiref.sync import sync_to_async
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackContext, ConversationHandler, JobQueue
)

# --- Django setup ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eLMS.settings')  # замените на ваш путь к settings.py
django.setup()

from main.models import Course, News, Faculty

SELECT_COURSE = 1

# Хранилище подписчиков (в простом варианте - в памяти, лучше в БД)
subscribers = set()

# Обертки для синхронных запросов к базе
@sync_to_async
def get_news_author_name(news):
    faculty = Faculty.objects.filter(id=news.faculty_id).first()
    return faculty.name if faculty else "Неизвестен"

@sync_to_async
def get_latest_news(last_id=None):
    qs = News.objects.order_by('-created_at')
    if last_id:
        qs = qs.filter(id__gt=last_id)
    return list(qs)

@sync_to_async
def get_new_courses(last_id=None):
    qs = Course.objects.order_by('-created_at')
    if last_id:
        qs = qs.filter(id__gt=last_id)
    return list(qs)

@sync_to_async
def get_all_courses():
    return list(Course.objects.all())

@sync_to_async
def get_course_by_name(name):
    return Course.objects.get(name=name)

@sync_to_async
def get_course_schedules(course):
    return list(course.schedule_set.all()) if hasattr(course, 'schedule_set') else []

# Для хранения последнего ID новостей и курсов 
last_news_id = 0
last_course_id = 0

# Команды для подписки/отписки
async def subscribe(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    await update.message.reply_text("Вы подписаны на уведомления о новых новостях и курсах.")

async def unsubscribe(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    subscribers.discard(chat_id)
    await update.message.reply_text("Вы отписаны от уведомлений.")

# Обработчики команд

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Я бот Центра по работе с НКО.\n"
        "Команды:\n"
        "/news — свежие новости\n"
        "/new_courses — новые курсы\n"
        "/schedule — расписание курсов\n"
        "/subscribe — подписаться на уведомления\n"
        "/unsubscribe — отписаться от уведомлений"
    )

@sync_to_async
def get_news_author_name(news):
    faculty = Faculty.objects.filter(id=news.faculty_id).first()
    return faculty.name if faculty else "Неизвестен"

@sync_to_async
def get_latest_news(last_id=None):
    qs = News.objects.order_by('-id')
    if last_id:
        qs = qs.filter(id__gt=last_id)
    return list(qs)

@sync_to_async
def get_new_courses(last_id=None):
    qs = Course.objects.order_by('-id')
    if last_id:
        qs = qs.filter(id__gt=last_id)
    return list(qs)

async def news(update: Update, context: CallbackContext):
    latest_news = await get_latest_news()
    if latest_news:
        messages = []
        for n in latest_news:
            author_name = await get_news_author_name(n)
            link = n.get_absolute_url() if hasattr(n, 'get_absolute_url') else 'нет ссылки'
            messages.append(f"{n.title}\nАвтор: {author_name}\nСсылка: {link}")
        text = "Свежие новости:\n" + "\n\n".join(messages)
    else:
        text = "Пока нет новостей."
    await update.message.reply_text(text)

# Функция рассылки новых новостей и курсов подписчикам
async def notify_updates(context: CallbackContext):
    global last_news_id, last_course_id
    bot = context.bot

    new_news = await get_latest_news(last_news_id)
    new_courses = await get_new_courses(last_course_id)

    for news in reversed(new_news):
        author_name = await get_news_author_name(news)
        link = news.get_absolute_url() if hasattr(news, 'get_absolute_url') else 'нет ссылки'
        message = f"📰 Новость: {news.title}\nАвтор: {author_name}\nСсылка: {link}"
        for chat_id in subscribers:
            try:
                await bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                print(f"Ошибка при отправке новости {news.id} пользователю {chat_id}: {e}")
        last_news_id = max(last_news_id, news.id)

    for course in reversed(new_courses):
        message = f"📚 Новый курс: {course.name} — {course.code}"
        for chat_id in subscribers:
            try:
                await bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                print(f"Ошибка при отправке курса {course.id} пользователю {chat_id}: {e}")
        last_course_id = max(last_course_id, course.id)

def main():
    TOKEN = "8118133343:AAHQGrj_tUN4Wzx4-W95nTD0-NaHs7Aav80"
    application = Application.builder().token(TOKEN).build()

    schedule_conv = ConversationHandler(
        entry_points=[CommandHandler('schedule', schedule)],
        states={
            SELECT_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_schedule)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('news', news))
    application.add_handler(CommandHandler('new_courses', new_courses))
    application.add_handler(CommandHandler('subscribe', subscribe))
    application.add_handler(CommandHandler('unsubscribe', unsubscribe))
    application.add_handler(schedule_conv)

    # Запускаем периодическую задачу уведомлений каждые 10 минут
    application.job_queue.run_repeating(notify_updates, interval=600, first=10)

    application.run_polling()

if __name__ == '__main__':
    main()
