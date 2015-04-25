import logging

import requests


class Trakttv(object):
    TRAKTTV_BASE_URL = u"https://api-v2launch.trakt.tv"
    l = logging.getLogger("trakttv")

    def __init__(self, client_id, client_secret=None):
        self.client_id = client_id
        self.client_secret = client_secret

        self.session = requests.Session()
        self.session.headers = {
            "trakt-api-key": self.client_id,
            "trakt-api-version": 2,
        }

    def all_shows_schedule(self, start_date, days):
        self.l.info("""\
Getting all-show-schedule from {start_date} for {days}""".format(
            start_date=start_date, days=days))

        url = u"{base_url}/calendars/all/shows/{start_date}/{days}".format(
            base_url=self.TRAKTTV_BASE_URL,
            start_date=start_date.isoformat(),
            days=days)
        r = self.session.get(url=url)

        self.l.info("Got all-show-schedule")
        self.l.debug(u"{}\t{}".format(r.status_code, r.text))

        r.raise_for_status()

        return r.json()
