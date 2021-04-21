class Room:
    def __init__(self, room_dict):
        self.__dict__.update(**room_dict)

    @property
    def sources(self):
        return self._sources

    @sources.setter
    def sources(self, sources_list):
        self._sources = []
        for source_dict in sources_list:
            self._sources.append(Source(source_dict))


class Source:
    def __init__(self, source_dict):
        self.__dict__.update(**source_dict)
