import time
import traceback

from twx.botapi import TelegramBot, ReplyKeyboardMarkup
from pyowm import OWM


def create_markup_keyboard(keyboard):
    """Creates a markup keyboard for telegram bot from keyboard

    Provides keyword arguments, that differ from default ones

    Parameters
    -----------------------
    keyboard: list
        The list contains lists of keyboard buttons

    return ReplyKeyboardMarkup
    """
    kwargs = {
        'one_time_keyboard': True,
        'resize_keyboard': True,
        'selective': False
    }
    return ReplyKeyboardMarkup(keyboard, **kwargs)


def message_from_observation(observation):
    """Gets weather from observation and processes it as a message
    to show to a user

    Parameters
    ---------------------
    observation:

    return str
        string contains current weather status, name of location, temperature and wind speed
    """
    weather = observation.weather
    location = observation.location

    status = weather.detailed_status
    place_name = location.name
    weather_time = str(weather.reference_time(timeformat='iso'))
    temperature = round(int(weather.temp['temp']) - 273.15, 1)
    wind = str(weather.wind()['speed'])

    return f'In {place_name} temperature is {temperature} C, status is {status} and wind is {wind} m/s'


def process_message(bot, owm, cities, update, state):
    """Handles updates from user and provides interface to a user

    Parameters
    -------------------------
    bot: TelegramBot
    owm: OWM
    cities: list
        provides a list of cities, which user can choose from
    update:
    state: dict
    """
    message = update.message
    chat_id = message.chat.id

    weather_mgr = owm.weather_manager()

    # create keyboard to provide start button
    keyboard = [[{'text': '/start'}]]
    start_keyboard = create_markup_keyboard(keyboard)

    # create keyboard to provide get weather button
    keyboard = [[{'text': 'Get weather'}], [{'text': 'Stop'}]]
    weather_keyboard = create_markup_keyboard(keyboard)

    # create keyboard to provide cities to choose from
    keyboard = [[{'text': city}] for city in cities]
    keyboard.append([{'text': 'Share location', 'request_location': True}])
    keyboard.append([{'text': 'Stop'}])
    reply_keyboard = create_markup_keyboard(keyboard)

    if state['started']:
        if message.sender and message.text and message.chat:
            text = message.text

            if text == 'Get weather':  # handle Get weather command
                bot.send_message(chat_id, 'Please, choose a city', reply_markup=reply_keyboard).wait()
            elif text in cities:  # handle city choice
                observation = weather_mgr.weather_at_place(text)

                msg = message_from_observation(observation)

                # interact with user
                bot.send_message(chat_id, msg)
                time.sleep(0.1)
                bot.send_message(chat_id, 'Please, select an option', reply_markup=reply_keyboard).wait()
            elif text == 'Stop':  # handle stop command
                state['started'] = False
                # interact with a user
                bot.send_message(chat_id, 'Execution stopped', reply_markup=start_keyboard).wait()
            else:
                # interact with a user
                bot.send_message(chat_id, 'Please, select an option', reply_markup=reply_keyboard).wait()
        elif message.location:  # if location provided
            loc = message.location
            observation = weather_mgr.weather_at_coords(loc.latitude, loc.longitude)

            msg = message_from_observation(observation)

            # interact with a user
            bot.send_message(chat_id, msg)
            bot.send_message(chat_id, 'Please, select an option', reply_markup=reply_keyboard).wait()
        else:
            print(update)
            bot.send_message(chat_id, 'Please, select an option', reply_markup=reply_keyboard).wait()
    else:
        if message.text == '/start':
            state['started'] = True
            bot.send_message(chat_id, 'Please, select an option', reply_markup=weather_keyboard).wait()


def main(TOKEN, OWM_KEY, cities):
    bot = TelegramBot(TOKEN)
    owm = OWM(OWM_KEY)
    state = {'started': False}

    last_update_id = 0

    bot.update_bot_info()

    while True:
        updates = bot.get_updates(offset=last_update_id).wait()
        try:
            for update in updates:
                if update.update_id > last_update_id:  # if this is not an old update
                    # handle update and move update id tracker
                    last_update_id = update.update_id
                    process_message(bot, owm, cities, update, state)
                    continue
            continue
        except Exception:  # if anything goes wrong and execution raises an error
            print(traceback.format_exc())
            continue


if __name__ == '__main__':
    # your telegram bot and weather api tokens
    TOKEN = ''
    OWM_KEY = ''

    # list of cities to choose from
    cities = ['London', 'Kazan', 'Moscow', 'Saint Petersburg', 'Hong Kong']
    main(TOKEN, OWM_KEY, cities)
