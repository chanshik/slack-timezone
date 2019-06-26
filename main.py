import os
import sys
import logging
import datetime
from collections import defaultdict

import pytz
import requests
from slack import WebClient, RTMClient

from setting import TRIGGER_KEYWORDS, WEATHER_TOKEN

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)
logger = logging.getLogger("slack_timezone_app")
web_client = None
rtm_client = None


def deg_to_compass(num) -> str:
    # Function code from https://stackoverflow.com/a/7490772
    val = int((num / 22.5) + .5)
    arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

    return arr[(val % 16)]


def call_openweathermap_by_timezone(tz_name) -> (bool, dict):
    weather_api = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': '',
        'appid': WEATHER_TOKEN,
        'units': 'metric'
    }

    try:
        city = tz_name.split("/")[1].replace('_', ' ')

    except RuntimeError:
        return False, {}

    params['q'] = city
    resp = requests.get(weather_api, params=params)
    if resp.status_code != 200:
        return False, {}

    try:
        weather_json = resp.json()

    except RuntimeError:
        return False, {}

    return True, weather_json


def get_weather_by_timezone(tz_name) -> str:
    if WEATHER_TOKEN is None or WEATHER_TOKEN == "":
        return ""

    success, weather_obj = call_openweathermap_by_timezone(tz_name)
    if success is False:
        return ""

    results = []
    main_prop = weather_obj['main']

    try:
        results.append('*{}°С*'.format(main_prop['temp']))
        if 'speed' in weather_obj['wind'] and 'deg' in weather_obj['wind']:
            speed = weather_obj['wind']['speed']
            deg = weather_obj['wind']['deg']
            results.append('wind *{} m/s* ({})'.format(speed, deg_to_compass(deg)))
        results.append('clouds *{} %*'.format(weather_obj['clouds']['all']))
        results.append('humidity *{} %*'.format(main_prop['humidity']))
        results.append('*{} hpa*'.format(main_prop['pressure']))

    except KeyError:
        return ""

    return ", ".join(results)


def get_timezone_with_user(user_id: str) -> tuple:
    tz_users = defaultdict(list)
    resp = web_client.users_list()
    members = resp.data['members']
    username = None

    for member in members:
        if not member['is_bot'] and member['name'] != 'slackbot':
            tz_users[member['tz']].append(member['name'])

            if member['id'] == user_id:
                username = member['name']

    now = datetime.datetime.utcnow().replace(microsecond=0)
    d = pytz.UTC.localize(now)

    results = ["*UTC*: *{}*".format(now.strftime("%Y-%m-%d %H:%M:%S%z %a"))]
    for tz_name, users in tz_users.items():
        tz = pytz.timezone(tz_name)
        results.append("*{}* ({})".format(tz_name, d.astimezone(tz).strftime("%Z")))
        results.append("  Local: *{}*".format(d.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S%z %a")))
        weather = get_weather_by_timezone(tz_name)
        if weather is not "":
            results.append("  Weather: {}".format(weather))
        results.append("  Users: *{}*".format(", ".join(["`{}`".format(u) for u in users])))

    return "\n".join(results), username


def check_trigger_keyword(data_text: str, keywords: list) -> bool:
    for keyword in keywords:
        if keyword in data_text:
            return True

    return False


@RTMClient.run_on(event='message')
def message_receiver(**payload):
    data = payload['data']
    client = payload['web_client']

    is_bot_message = 'subtype' in data and data['subtype'] != 'bot_message'

    if not is_bot_message and 'text' in data and check_trigger_keyword(data['text'], TRIGGER_KEYWORDS):
        channel_id = data['channel']
        tz_results, username = get_timezone_with_user(data['user'])

        client.chat_postMessage(
            channel=channel_id,
            text=tz_results
        )

        logger.info("{} request timezone.".format(username))

    else:
        pass


@RTMClient.run_on(event='hello')
def hello(**payload):
    logger.info("RTM Connected.")


def main():
    global web_client, rtm_client, WEATHER_TOKEN

    token = os.getenv("SLACK_TOKEN", "")
    if token == "":
        logger.error("SLACK_TOKEN is empty. Exiting.")
        sys.exit(255)

    WEATHER_TOKEN = os.getenv("WEATHER_TOKEN", WEATHER_TOKEN)
    if WEATHER_TOKEN == "":
        logger.warning("WEATHER_TOKEN is empty. 'Print weather of the region' is disabled.")

    web_client, rtm_client = init_client(token)
    if web_client is None or rtm_client is None:
        logger.error("Initialize failed. Exiting.")
        sys.exit(254)

    if not check(web_client):
        logger.error("API Check failed. Exiting.")
        sys.exit(253)

    logger.info("RTM Client starting.")
    rtm_client.start()


def check(web_client) -> bool:
    resp = web_client.api_test()

    return resp.data['ok']


def init_client(token):
    web_client = WebClient(token=token)
    rtm_client = RTMClient(token=token)

    return web_client, rtm_client


if __name__ == '__main__':
    main()
