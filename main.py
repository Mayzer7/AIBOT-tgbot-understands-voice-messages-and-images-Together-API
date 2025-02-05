import telebot
import requests
import speech_recognition as sr
from pydub import AudioSegment

from PIL import Image
import pytesseract
from io import BytesIO
import html

# Инициализация бота и API
BOT_TOKEN = 'your_bot_token'
TOGETHER_API_KEY = 'your_together_api_key'

bot = telebot.TeleBot(BOT_TOKEN)

# URL API Together.AI
API_URL = "https://api.together.ai/v1/chat/completions"

# Заголовки для API-запроса
HEADERS = {
    "Authorization": f"Bearer {TOGETHER_API_KEY}",
    "Content-Type": "application/json"
}

# Память для хранения текста из изображений (отдельно для каждого пользователя)
user_memory = {}

# Если сгенирированный ответ бота больше чем 4096 символов, то он делится на несколько сообщений
def send_formatted_message(chat_id, text, chunk_size=4096):
    paragraphs = text.split('\n')
    current_chunk = ""
    
    for para in paragraphs:
        # Экранируем абзац, чтобы исключить неподдерживаемые HTML-теги
        para = html.escape(para)
        if len(current_chunk) + len(para) + 1 > chunk_size:
            bot.send_message(chat_id, current_chunk, parse_mode='HTML')
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n" + para
            else:
                current_chunk = para

    if current_chunk:
        bot.send_message(chat_id, current_chunk, parse_mode='HTML')

# Функция преобразования голосового сообщения в текст
def transcribe_audio(audio_file_url):
    try:
        # Загружаем аудиофайл
        audio_data = requests.get(audio_file_url).content
        
        # Сохраняем временный файл
        with open('temp.ogg', 'wb') as f:
            f.write(audio_data)

        # Конвертируем OGG в WAV
        audio = AudioSegment.from_ogg('temp.ogg')
        audio.export('temp.wav', format="wav")
        
        # Инициализируем recognizer
        recognizer = sr.Recognizer()

        # Загружаем аудио в SpeechRecognition
        with sr.AudioFile('temp.wav') as source:
            audio = recognizer.record(source)  # Чтение всего аудио файла
        
        # Преобразуем аудио в текст с помощью Google Speech Recognition
        text = recognizer.recognize_google(audio, language="ru-RU")
        return text
    except sr.UnknownValueError:
        return "Не удалось распознать речь"
    except sr.RequestError:
        return "Ошибка сервиса распознавания речи"
    except Exception as e:
        return f"Ошибка обработки аудио: {str(e)}"

# Функция распознаёт текст с изображения с использованием Tesseract OCR.
def recognize_text_from_image(image_url):
    try:
        image_data = requests.get(image_url).content
        image = Image.open(BytesIO(image_data))
        image = image.convert("L").point(lambda x: 0 if x < 128 else 255)
        extracted_text = pytesseract.image_to_string(image, lang="rus+eng", config=r'--oem 3 --psm 6').strip()
        return extracted_text if extracted_text else "Текст не найден"
    except Exception as e:
        return f"Ошибка обработки изображения: {str(e)}"


# Общение с ИИ моделью
def chat_with_llama(user_message):
    try:
        data = {"model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "messages": [{"role": "user", "content": user_message}], "temperature": 0.7, "max_tokens": 1500}
        response = requests.post(API_URL, headers=HEADERS, json=data)
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "Ошибка API")
    except Exception as e:
        return f"Ошибка при обработке запроса: {str(e)}"

# Обработчик команды /start
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я могу ответить на любой вопрос и решить любую задачу. Пиши мне или отправляй фото, по ходу разберёмся)")

# Обработчик команды /clear
@bot.message_handler(commands=["clear"])
def clear_memory(message):
    user_memory[message.chat.id] = []
    bot.send_message(message.chat.id, "Контекст очищен.")

# Обработчик голосовых сообщений
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        # Получаем файл голосового сообщения
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        
        # Получаем URL для скачивания файла
        file_url = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
        
        # Преобразуем голосовое сообщение в текст
        text = transcribe_audio(file_url)
        
        # Запрашиваем ответ от Together.AI
        ai_response = chat_with_llama(text)
        
        # Отправляем текст пользователю
        bot.send_message(message.chat.id, f'Распознанное сообщение: {text}\n\nОтвет ИИ: {ai_response}')
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка обработки голосового сообщения: {str(e)}")

# Обработка изображений
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}'
        extracted_text = recognize_text_from_image(file_url)
        
        if extracted_text and extracted_text != "Текст не найден":
            user_memory.setdefault(message.chat.id, []).append(extracted_text)
            bot.send_message(message.chat.id, f"Текст сохранён: {extracted_text}\n\nВы можете продолжить работу с ним.")
        else:
            bot.send_message(message.chat.id, "Текст не найден.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка обработки фото: {str(e)}")

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    if chat_id in user_memory and user_memory[chat_id]:
        context = "\n".join(user_memory[chat_id])
        response = chat_with_llama(f"Контекст: {context}\nПользователь: {message.text}")
    else:
        response = chat_with_llama(message.text)
    send_formatted_message(chat_id, response)

# Бесконечная работа бота
bot.polling(non_stop=True)