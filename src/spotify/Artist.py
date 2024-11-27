class Artist:
    id: str
    name: str

    def __init__(self, id, name) -> None:
        self.id = id
        self.name = name

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['id'],
            data['name'],
        )
