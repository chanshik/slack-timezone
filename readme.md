# Slack Timezone Bot

## Purpose

Show members' timezone and each local time.

## Environments

### Python 3.x
* slackclient
* requests

```
$ pip install -r requirements
```

### API Keys
* Slack Token
* https://openweathermap.org API Key

## Run

```
$ export SLACK_TOKEN="xoxb-xxxx"
$ export WEATHER_TOKEN="xxxxxxxxxxx"
$ python main.py
```

## To Do

- [x] Print name of the day
- [x] Print weather of the timezone
- [x] Add more trigger word
- [ ] Add Supervisor environments
- [ ] Add Dockerfile
