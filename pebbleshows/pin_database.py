import pymongo


class PinDatabase(object):
    pins_collection_name = "pins"

    def __init__(self, mongodb_url):
        self._mongo_client = pymongo.MongoClient(mongodb_url)
        self._db = self._mongo_client.get_default_database()
        self.db_pins = self._db[self.pins_collection_name]

    def upsert(self, pin, metadata=None, **kwargs):
        if metadata is None:
            metadata = {}
        metadata.update(kwargs)

        return self.db_pins.replace_one(
            filter={'pin.id': pin["id"]},
            replacement={
                'pin': pin,
                'metadata': metadata,
            },
            upsert=True,
        )

    def all_pin_ids(self):
        cursor = self.db_pins.find(projection={'pin.id': True})

        pin_ids = {el['pin']['id'] for el in cursor}

        return pin_ids

    def pin_for_launch_code(self, launch_code):
        pin = self.db_pins.find_one({'pin.actions.launchCode': launch_code})
        if pin is None:
            raise KeyError("No pin for launch_code {}".format(launch_code))
        return pin
