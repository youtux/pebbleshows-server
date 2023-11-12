from __future__ import print_function, unicode_literals
import datetime
import os
import random
import logging
import concurrent.futures

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pypebbleapi


from trakttv import Trakttv
from pin_database import PinDatabase


TRAKTV_CLIENT_ID = os.environ["TRAKTV_CLIENT_ID"]
MONGODB_URL = os.environ["MONGODB_URL"]
PEBBLE_TIMELINE_API_KEY = os.environ["PEBBLE_TIMELINE_API_KEY"]

timeline = pypebbleapi.Timeline(api_key=PEBBLE_TIMELINE_API_KEY)
trakttv = Trakttv(TRAKTV_CLIENT_ID)
pins_db = PinDatabase(MONGODB_URL)

l = logging.getLogger("scheduler")


def create_episode_pin(
        pin_id,
        date,
        duration,
        show_title,
        season_number,
        episode_number,
        episode_title,
        ):
    if not show_title:
        show_title = "Unknown show"

    season_episode_str = "S{season:0>2}E{episode:0>2}".format(
        season=season_number, episode=episode_number)

    # pin_title = show_title
    pin_title = f"{show_title} | {season_episode_str}"

    if not episode_title:
        episode_title = ""

    pin = {
        "id": pin_id,
        "time": date,
        "duration": duration,
        "layout": {
            "type": "calendarPin",
            # "shortTitle": pin_short_title,
            "title": pin_title,
            # "subtitle": season_episode_str,
            "body": episode_title,
            "tinyIcon": "system://images/MOVIE_EVENT",
        },
        "actions": [
            {
                "title": "Check-in",
                "type": "openWatchApp",
                "launchCode": random.randint(0, 2**32 - 1)
            },
            {
                "title": "Mark as seen",
                "type": "openWatchApp",
                "launchCode": random.randint(0, 2**32 - 1)
            },
        ]
    }
    # Remove None values
    if pin["duration"] is None:
        del pin["duration"]
    if not pin["layout"]["body"]:
        del pin["layout"]["body"]

    return pin


def send_and_log_pin(pin, topics, metadata):
    response = timeline.send_shared_pin(topics, pin)
    try:
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        l.error(e)
        l.error(response.content)
        return
    pins_db.upsert(pin, metadata)

    l.info(
        f'Pin (id={pin["id"]}, title={pin["layout"].get("title", None)}) sent and updated.'
    )


def fetch_shows_and_send_pins():
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=3)

    days = 15

    try:
        calendar = trakttv.all_shows_schedule(
            start_date=start_date, days=days)
    except requests.exceptions.HTTPError as e:
        l.error(e)
        return

    pin_ids_already_sent = pins_db.all_pin_ids()

    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        # Start the load operations and mark each future with its URL

        for ep_schedule in calendar:
            episode_id = ep_schedule["episode"]["ids"]["trakt"]
            show_id = ep_schedule["show"]["ids"]["trakt"]
            pin_id = "schedule-{episode_id}".format(episode_id=episode_id)

            if pin_id in pin_ids_already_sent:
                l.debug(f"Pin (id={pin_id}) already sent. skipping.")
                continue

            pin = create_episode_pin(
                pin_id=pin_id,
                date=ep_schedule["first_aired"],
                duration=40,
                show_title=ep_schedule["show"]["title"],
                season_number=ep_schedule["episode"]["season"],
                episode_number=ep_schedule["episode"]["number"],
                episode_title=ep_schedule["episode"]["title"],
            )
            metadata = {
                'episodeID': episode_id,
            }
            # send_and_log_pin(topics=[show_id], pin=pin, metadata=metadata)
            futures.append(executor.submit(
                send_and_log_pin, topics=[show_id], pin=pin, metadata=metadata)
            )
        for _ in concurrent.futures.as_completed(futures):
            pass

    print("End of the job")


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger("pebble-timeline").setLevel(logging.DEBUG)
    logging.getLogger("trakttv").setLevel(logging.INFO)
    logging.getLogger("scheduler").setLevel(logging.INFO)

    fetch_shows_and_send_pins()

    every_night = CronTrigger(hour=3, minute=0, second=40)
    scheduler = BlockingScheduler()

    scheduler.add_job(fetch_shows_and_send_pins, trigger=every_night)
    scheduler.start()
