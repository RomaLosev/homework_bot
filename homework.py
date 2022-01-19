from http import HTTPStatus
from dotenv import load_dotenv
import telegram
import requests
import os
import logging
import time

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='main.log',
    level=logging.INFO,
    filemode='a'
)


def send_message(bot, message):
    """Отправляем сообщение."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    chat_id = TELEGRAM_CHAT_ID
    logging.info(f'Message send {message}')
    return bot.send_message(chat_id, text=message)


def get_api_answer(current_timestamp):
    """Берём информацию с сервера."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != HTTPStatus.OK:
        raise Exception("invalid response")
    logging.info('server respond')
    return homework_statuses.json()


def check_response(response):
    """Проверка полученной информации."""
    homeworks = response['homeworks']
    if homeworks is None:
        raise Exception("Нет домашней работы")
    if type(homeworks) != list:
        raise TypeError("Не словарь")
    return homeworks


def parse_status(homework):
    """Достаем статус работы."""
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_STATUSES[homework.get('status')]
    if homework_name is None:
        raise KeyError("No homework name")
    if verdict is None:
        raise Exception("No verdict")
    logging.info(f'got verdict {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность токенов."""
    if TELEGRAM_TOKEN or TELEGRAM_CHAT_ID is not None:
        return True
    elif PRACTICUM_TOKEN is not None:
        return True
    else:
        return False


def main():
    """Главный цикл работы."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            get_api_answer_result = get_api_answer(current_timestamp)
            check_response_result = check_response(get_api_answer_result)
            if check_response_result:
                for homework in check_response_result:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
            time.sleep(RETRY_TIME)
        except Exception as error:
            logging.error('Бот сломался')
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f'Сбой в работе программы: {error}'
            )
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
