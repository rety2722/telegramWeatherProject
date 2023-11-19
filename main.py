import json
import requests
import time
import urllib
import logging
import signal
import sys

TOKEN = '6335691511:AAFbvY9wj0pck6vZKKYy_LpkKoSAxmbrpF0'
OWM_KEY = 'bd5b3480cf228022801bad6280ae2c69'
POLLING_TIMEOUT = None


def get_text(update):
    """Gets text from the message """
    return update['message']['text']


def get_location(update):
    """Gets location from the message"""
    if 'text' in update['message']:
        return update['message']['text']
    elif 'location' in update['message']:
        return update['message']['location']


def get_chat_id(update):
    """Gets chat id from the message """
    return update['message']['chat']['id']


def get_up_id(update):
    """Returns the update id """
    return int(update['update_id'])


def get_result(updates):
    """Returns the result of updates"""
    return updates['result']


def get_description(weather):
    """Gets weather description"""
    return weather['weather'][0]['description']


def get_temperature(weather):
    """Gets temperature from weather"""
    return weather['main']['temp']


def get_city(weather):
    """Gets a city name"""
    return weather['name']


logger = logging.getLogger('weather-telegram')
logger.setLevel(logging.DEBUG)

cities = ['Kazan', 'Moscow', 'London', 'Hong Kong']


def sig_handler(signal, frame):
    logger.info("SIGINT received. Exiting... Bye bye")
    sys.exit(0)


def config_logging():
    """ Creates file 'run.log' and gives DEBUG and INFO information
    in the file in a formatted manner
    """
    handler = logging.FileHandler('run.log', mode='w')
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(levelname)s] - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def parse_config():
    """ Creates parsing configuration by creating URLs for telegram bot and OWM"""
    global URL, URL_OWM, POLLING_TIMEOUT
    URL = "https://api.telegram.org/bot{}/".format(TOKEN)
    URL_OWM = "https://api.openweathermap.org/data/2.5/weather?appid={}&units=metric".format(OWM_KEY)
    POLLING_TIMEOUT


def make_request(url):
    """makes request to the specified url
    returns response in json format"""
    logger.debug('URL: %s' % url)
    return requests.get(url).json()


def get_updates(offset=None):
    """Gets all updates with IDs more than offset
    """
    url = URL + 'getUpdates?timeout=%s' % POLLING_TIMEOUT
    logger.info('Getting updates')
    if offset:
        url += '&offset={}'.format(offset)
    return make_request(url)


def build_keyboard(items):
    """Builds custom keyboard from items"""
    keyboard = [[{'text': item}] for item in items]
    keyboard.append([{'text': '/end'}])
    reply_keyboard = {'keyboard': keyboard, 'one_time_keyboard': True}
    logger.debug(reply_keyboard)
    return json.dumps(reply_keyboard)


def build_cities_keyboard():
    """Builds keyboard with cities provided"""
    keyboard = [[{'text': city}] for city in cities]
    keyboard.append([{'text': 'Share Location', 'request_location': True}])
    keyboard.append([{'text': '/end'}])
    reply_keyboard = {'keyboard': keyboard, 'one_time_keyboard': True}
    logger.debug(reply_keyboard)
    return json.dumps(reply_keyboard)


def get_weather(place):
    """Gets weather in place, shows temperature, description and city"""
    if isinstance(place, dict):
        lat, lon = place['latitude'], place['longitude']
        url = URL_OWM + '&lat=%f&lon=%f&cnt=1' % (lat, lon)
        logger.info('Requesting weather: ' + url)
        request = make_request(url)
        logger.debug(request)
        return u"%s \N{DEGREE SIGN}C, %s in %s" % (
            get_temperature(request), get_description(request), get_city(request))
    else:
        url = URL_OWM + '&q={}'.format(place)
        logger.info('Requesting weather: ' + url)
        request = make_request(url)
        logger.debug(request)
        return u"%s \N{DEGREE SIGN}C, %s in %s" % (
            get_temperature(request), get_description(request), get_city(request))


def send_message(text, chat_id, interface=None):
    """Sends a message to a chat with given id via
    given interface
    """
    text = text.encode('utf-8', 'strict')
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if interface:
        url += "&reply_markup={}".format(interface)
    requests.get(url)


def get_last_update(updates):
    """Finds the ID of the last available update"""
    return max([get_up_id(u) for u in get_result(updates)])


# will keep tracks of conversation states
chats = {}
# to keep track of whether the execution is started
started = False


def handle_updates(updates):
    """Handles all the processing: checks for new messages
    if finds any, processes them"""
    global started
    for update in get_result(updates):
        chat_id = get_chat_id(update)
        try:
            text = get_text(update)
        except Exception as e:
            logger.error('No text field to update. Try to get location')
            loc = get_location(update)
            if chat_id in chats and chats[chat_id] == 'weather_request':
                logger.info("Weather requested for %s in chat id %d" % (str(loc), chat_id))
                # Send weather to chat id and clear state
                send_message(get_weather(loc), chat_id)
                keyboard = build_cities_keyboard()
                send_message('Do you wish to know the weather in another city', chat_id, keyboard)
                # del chats[chat_id]
            continue
        if text == '/start':
            keyboard = build_keyboard(['/weather'])
            send_message('Read the instructions carefully', chat_id, keyboard)
            started = True
            logger.info('The execution started')
        elif started and text:
            if text == '/weather':
                keyboard = build_cities_keyboard()
                chats[chat_id] = 'weather_request'
                send_message('Select a city', chat_id, keyboard)
            elif text.startswith('/'):
                logger.warning('Invalid command %s' % text)
            elif (text in cities) and (chat_id in chats) and (chats[chat_id] == 'weather_request'):
                logger.info('Weather requested for %s' % text)
                send_message(get_weather(text), chat_id)
                keyboard = build_cities_keyboard()
                send_message('Do you wish to know the weather in another city', chat_id, keyboard)
                # del chats[chat_id]
            elif text == '/end':
                send_message('Please, enter /start if you wish to know the weather', chat_id)
                started = False
            else:
                keyboard = build_keyboard(['/weather'])
                send_message('You can ask me about the weather', chat_id, keyboard)
        elif text:
            send_message('Invalid command %s' % text, chat_id)


def main():
    config_logging()

    parse_config()

    signal.signal(signal.SIGINT, sig_handler)

    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if len(get_result(updates)) > 0:
            last_update_id = get_last_update(updates) + 1
            handle_updates(updates)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
