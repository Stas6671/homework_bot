from json import JSONDecodeError
import logging
import sys
import requests
import os
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()

ONE_MONTH_UNIX = 2629743

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = '1099215744'

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except telegram.error.TelegramError as error:
        raise telegram.error.TelegramError(
            f'Ошибка отправки сообщения: {error}.'
        )
    logging.debug(
        'Сообщение успешно отправлено.'
    )


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.exceptions.RequestException:
        raise ConnectionError(
            'Ошибка запроса к эндпоинту.'
        )
    if response.status_code != HTTPStatus.OK:
        raise requests.HTTPError(
            f'Ошибка запроса к эндпоинту: {response.status_code}'
        )
    try:
        return response.json()
    except JSONDecodeError:
        raise JSONDecodeError(
            'Ответ сервера не преобразовывается в JSON.'
        )


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ API домашки не словарь.'
        )
    if 'homeworks' not in response:
        raise KeyError(
            'В ответе API домашки нет ключа "homeworks".'
        )
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Ответ API домашки под ключом `homeworks` не список.'
        )
    homework = response.get('homeworks')
    return homework


def parse_status(homework):
    """Извлекает статус домашней работы."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError(
            'Такой домашней работы нет.'
        )
    if status not in HOMEWORK_VERDICTS:
        raise KeyError(
            'Недокументированный статус домашней работы.'
        )
    if not homework:
        raise KeyError(
            'Список домашних работ пуст.'
        )
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Ошибка доступности переменных.'
        )
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - ONE_MONTH_UNIX
    error_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)[0]
            message = parse_status(homework)
            send_message(bot, message)
            timestamp = response.get('current_date', timestamp)
            error_message = ''
        except telegram.TelegramError as error:
            logging.error(
                f'Ошибка отправки сообщения: {error}.'
            )
        except Exception as error:
            logging.error(
                f'Сбой в работе программы: {error}'
            )
            message = f'Сбой в работе программы: {error}'
            if error_message != message:
                send_message(bot, message)
                error_message != message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='bot_log.log',
        filemode='w',
        level=logging.DEBUG
    )
    main()
