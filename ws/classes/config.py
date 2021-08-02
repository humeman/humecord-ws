import yaml
import aiofiles

class Config:
    def __init__(
            self,
            path: str
        ):

        self._path = path

    async def _load(
            self
        ):

        async with aiofiles.open("config.yml", "r") as f:
            self._data = yaml.safe_load(await f.read())

        for name, value in self._data.items():
            if name.startswith("_"):
                continue

            setattr(self, name, value)

    