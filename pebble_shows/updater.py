from __future__ import print_function, unicode_literals
import datetime
import os
import random
import logging
import collections

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from trakttv import Trakttv
from pin_database import PinDatabase
import pebble


TRAKTV_CLIENT_ID = os.environ["TRAKTV_CLIENT_ID"]
MONGODB_URL = os.environ["MONGODB_URL"]
PEBBLE_TIMELINE_API_KEY = os.environ["PEBBLE_TIMELINE_API_KEY"]
DAYS_LOOKAHEAD = os.environ.get("DAYS_LOOKAHEAD", 15)

ObjectResult = collections.namedtuple("ObjectResult",
    ("pin", "metadata", "future"))


def create_episode_pin(
        pin_id,
        date,
        duration,
        show_title,
        season_number,
        episode_number,
        episode_title,
        ):
    season_episode_str = "S{season:0>2}E{episode:0>2}".format(
        season=season_number, episode=episode_number)
    if show_title:
        pin_title = "{} | {}".format(show_title, season_episode_str)
    else:
        pin_title = season_episode_str

    pin = {
        "id": pin_id,
        "time": date,
        "duration": duration,
        "layout": {
            "type": "calendarPin",
            "title": pin_title,
            "body": episode_title,
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
    if pin["layout"]["body"] is None:
        del pin["layout"]["body"]

    return pin


def fetch_shows_and_send_pins():
    l = logging.getLogger("scheduler")

    timeline = pebble.Timeline(api_key=PEBBLE_TIMELINE_API_KEY)
    trakttv = Trakttv(TRAKTV_CLIENT_ID)
    pins_db = PinDatabase(MONGODB_URL)

    try:
        calendar = trakttv.all_shows_schedule(
            start_date=datetime.date.today() - datetime.timedelta(days=1),
            days=DAYS_LOOKAHEAD)
    except requests.exceptions.HTTPError as e:
        l.error(e)
        return

    pin_ids_already_sent = pins_db.all_pin_ids()
    #TODO use pebble (on pypi, nothing to do with this file)
    pin_insertion_results = []

    for ep_schedule in calendar:
        episode_id = ep_schedule["episode"]["ids"]["trakt"]
        show_id = ep_schedule["show"]["ids"]["trakt"]
        pin_id = "schedule-{episode_id}".format(episode_id=episode_id)

        if pin_id in pin_ids_already_sent:
            l.debug("Pin (id={}) already sent. skipping.".format(pin_id))
            continue

        pin = create_episode_pin(
            pin_id=pin_id,
            date=ep_schedule["first_aired"],
            duration=60,
            show_title=ep_schedule["show"]["title"],
            season_number=ep_schedule["episode"]["season"],
            episode_number=ep_schedule["episode"]["number"],
            episode_title=ep_schedule["episode"]["title"],
        )
        metadata = {
            'episodeID': episode_id,
        }

        future = timeline.send_shared_pin(pin, [show_id])
        pin_insertion_results.append(ObjectResult(pin, metadata, future))

    for pr in pin_insertion_results:
        response = pr.future.result()
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            l.error(e)
            return
        pins_db.upsert(pr.pin, pr.metadata)

        l.info("Pin (id={}, title={}) sent and updated.".format(
            pin["id"],
            pin["layout"].get("title", None),
            )
        )
        l.debug(pin)


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
