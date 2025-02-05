
# How to install guide

## Активация виртуального окружения
```bash
Откройте терминал и выполните:
python3 -m venv venv
source venv/bin/activate
```

---

## Установка библиотек
```bash
pip3 install -r requirements.txt
```

---

## Подготовка к запуску модуля main.py
```bash
Внутри файла вам нужно подсатвить значения в эти поля:
# Инициализация бота и API
BOT_TOKEN = 'your_tgbot_token'
TOGETHER_API_KEY = 'your_together_api_key'

BOT_TOKEN вы можете получить через бота в телеграмм BotFather (гугл в помощь)
TOGETHER_API_KEY перейдите на сайт https://api.together.ai/ авторизируйтесь и сразу же вам выдадут ключ, подставьте его в эту переменную
После чего можете успешно запускать модуль и бот будет работать - в терминале python3 main.py
```
