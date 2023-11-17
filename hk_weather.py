import requests

from weather import Weather

URL = 'https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType={dataType}&lang={lang}'


def get_hk_weather_data(data_type='rhrread', lang='en'):
    response = requests.get(url=URL.format(dataType=data_type, lang=lang))
    return response.json()
