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
PRACTICUM_ENDPOINT = (
    'https://practicum.yandex.ru/api/user_api/homework_statuses/'
)
PRACTICUM_HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

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
    logging.info(f'Сообщение отправлено {message}')
    try:
        return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except ConnectionError:
        logging.error('Сервер не отвечает')


def get_api_answer(current_timestamp):
    """Берём информацию с сервера."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            PRACTICUM_ENDPOINT, headers=PRACTICUM_HEADERS, params=params
        )
    except requests.RequestException:
        logging.error('Сервер не отвечает')
    if homework_statuses.status_code != HTTPStatus.OK:
        raise Exception('Неверный запрос')
    logging.info('Сервер на связи')
    try:
        return homework_statuses.json()
    except ValueError:
        logging.error('Неверное значение')
        raise Exception('Неверное значение')


def check_response(response):
    """Проверка полученной информации."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logging.error('Такого ключа в словаре нет')
        raise Exception('Такого ключа в словаре нет')
    if isinstance(homeworks, dict):
        raise TypeError('Ответ не является списком')
    return homeworks


def parse_status(homework):
    """Достаем статус работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Нет такой домашней работы')
    try:
        verdict = HOMEWORK_STATUSES[homework.get('status')]
    except KeyError:
        logging.error('Нет такого значения в словаре')
        raise KeyError('Нет такого значения в словаре')
    if verdict is None:
        raise Exception('Вердикт не вынесен')
    logging.info(f'Вердикт: {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность токенов."""
    tokens = [TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN]
    return all(tokens)


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
        except Exception as error:
            logging.error('Бот сломался')
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f'Сбой в работе программы: {error}'
            )
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
