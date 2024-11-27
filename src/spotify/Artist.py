from os import name


class Artist:
    id: str
    name: str

    def __init__(self, id, name) -> None:
        self.id = id
        self.name = name
