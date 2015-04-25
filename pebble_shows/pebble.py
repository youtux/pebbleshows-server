import logging

from requests_futures.sessions import FuturesSession
#TODO use pebble (on pypi, nothing to do with this file)

class Timeline(object):
    TIMELINE_BASE_URL = "https://timeline-api.getpebble.com"
    l = logging.getLogger("pebble-timeline")

    def __init__(self, api_key):
        self.api_key = api_key

        self.shared_pin_session = FuturesSession()
        self.shared_pin_session.headers = {
            'X-API-Key': self.api_key,
        }
        self.user_pin_session = FuturesSession()

    def send_shared_pin(self, pin, topics):
        self.l.info("""\
Sending shared pin (id={pin_id}) for topics: {topics}""".format(
                pin_id=pin["id"], topics=topics))
        url = "{base_url}/v1/shared/pins/{pin_id}".format(
            base_url=self.TIMELINE_BASE_URL,
            pin_id=pin["id"]
        )

        r = self.shared_pin_session.put(
            url=url,
            json=pin,
            headers={
                'X-Pin-Topics': ",".join(str(t) for t in topics),
            },
        )
        self.l.info("""\
Shared pin (id={pin_id}) sent succesfully""".format(pin_id=pin["id"]))
        # self.l.debug(u"{}\t{}".format(r.status_code, r.text))

        return r
