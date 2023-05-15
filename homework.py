import logging
import requests
import os
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()

ONE_MONTH_UNIX = 2629743
OLD_STATUS = ''

PRACTICUM_TOKEN = 'y0_AgAAAABfxnlAAAYckQAAAADiRp9wzgiPdhBOQYiH1yDJN9ltad080Do'
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
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID is not None:
        return True
    else:
        logging.critical(
            'Ошибка доступности переменных.'
        )
        return False


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(
            'Сообщение успешно отправлено.'
        )
    except telegram.error.TelegramError as error:
        logging.error(
            f'Ошибка отправки сообщения: {error}.'
        )
        raise telegram.error.TelegramError(
            f'Ошибка отправки сообщения: {error}.'
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
        logging.error(
            'Ошибка запроса к эндпоинту.'
        )
        raise ConnectionError(
            'Ошибка запроса к эндпоинту.'
        )
    try:
        isinstance(response.json, dict)
    except TypeError:
        logging.error(
            'Неверный тип данных.'
        )
        raise TypeError(
            'Неверный тип данных.'
        )
    if response.status_code != HTTPStatus.OK:
        logging.error(
            f'Ошибка запроса к эндпоинту: {response.status_code}'
        )
        raise requests.HTTPError(
            f'Ошибка запроса к эндпоинту: {response.status_code}'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error(
            'Ответ API домашки не словарь.'
        )
        raise TypeError(
            'Ответ API домашки не словарь.'
        )
    if 'homeworks' not in response:
        logging.error(
            'В ответе API домашки нет ключа "homeworks".'
        )
        raise KeyError(
            'В ответе API домашки нет ключа "homeworks".'
        )
    if not isinstance(response.get('homeworks'), list):
        logging.error(
            'Ответ API домашки под ключом `homeworks` не список.'
        )
        raise TypeError(
            'Ответ API домашки под ключом `homeworks` не список.'
        )
    else:
        homework = response.get('homeworks')
        return homework


def parse_status(homework):
    """Извлекает статус домашней работы."""
    global OLD_STATUS
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logging.error(
            'Такой домашней работы нет.'
        )
        raise KeyError(
            'Такой домашней работы нет.'
        )
    if status not in HOMEWORK_VERDICTS:
        logging.error(
            'Недокументированный статус домашней работы.'
        )
        raise KeyError(
            'Недокументированный статус домашней работы.'
        )
    if status == OLD_STATUS:
        logging.debug('Изменений нет.')
    else:
        verdict = HOMEWORK_VERDICTS[status]
        OLD_STATUS = status
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - ONE_MONTH_UNIX

    while True:
        if check_tokens() is False:
            break
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)[0]
            message = parse_status(homework)
            send_message(bot, message)
        except telegram.TelegramError as error:
            logging.error(
                f'Ошибка отправки сообщения: {error}.'
            )
        except ConnectionError as error:
            message = f'Ошибка запроса к эндпоинту: {error}.'
            send_message(bot, message)
        except TypeError as error:
            message = f'Неверный тип данных: {error}.'
            send_message(bot, message)
        except KeyError as error:
            message = f'Ошибка ключей или значений: {error}.'
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
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
