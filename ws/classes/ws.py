from .config import Config

import websockets
import asyncio
import json
import time
import traceback

from typing import Optional, Tuple

class HumecordWebsocket:
    def __init__(
            self
        ):

        # Load up config
        self.config = Config("config.yml")

        # Prepare clients
        self.clients = {}

        self.actions = {}

    def start(
            self
        ) -> None:
        """
        Starts the event loop and websocket.
        """

        asyncio.get_event_loop().run_until_complete(self.async_start())
        asyncio.get_event_loop().run_forever()

    async def async_start(
            self
        ) -> None:
        """
        Loads stuff, then starts the socket.
        """

        await self.config._load()

        await self.start_websocket()

    async def start_websocket(
            self
        ) -> None:
        """
        Starts the asynchronous websocket.
        """

        await websockets.serve(
            self.wrap_recv,
            self.config.host,
            self.config.port
        )

    async def wrap_recv(
            self,
            websocket,
            path
        ) -> None:

        bot = {
            "bot": None
        }

        try:
            await self.recv(
                self,
                websocket,
                path,
                bot
            )

        except (websockets.exceptions.ConnectionClosedError) as e:
            # Delete from storage
            # Update: I will be doing that
            pass

        if bot["bot"] is not None:
            if bot["bot"] in self.clients:
                del self.clients[bot["bot"]]

            # Send disconnect message
            for client in self.config.status_clients:
                if client in self.clients:
                    await self.send(
                        self.clients[client]["socket"],
                        {
                            "type": "response",
                            "action": "send_offline",
                            "data": {
                                "bot": bot["bot"]
                            }
                        }
                    )
                    return

    async def recv(
            self,
            websocket,
            path,
            bot_
        ) -> None:

        auth = False
        bot = None

        async for message in websocket:
            if type(message) != str:
                await self.error(websocket, "Invalid message type - only JSON is accepted")
                continue

            # Parse the message
            try:
                action, data = await self.parse(websocket, message)
            
            except Exception as e:
                await self.error(websocket, f"{str(e)}")
                await websocket.close()
                return

            if not auth:
                if action != "auth":
                    await self.error(websocket, "Not authenticated")
                    continue

                allowed, bot = await self.auth(
                    websocket,
                    data.get("key")
                )

                if not allowed:
                    await self.error(websocket, bot)
                    await websocket.close()
                    return

                bot_["bot"] = bot

                if bot in self.clients:
                    if not self.clients[bot]["socket"].closed:
                        try:
                            await self.clients[bot]["socket"].close()

                        except:
                            pass

                    del self.clients[bot]

                        #await self.error(websocket, f"Bot {bot} is already connected")
                        #await websocket.close()
                        #return

                # Register to database
                self.clients[bot] = {
                    "socket": websocket,
                    "login": time.time(),
                    "addr": websocket.remote_address[0]
                }

                auth = True

            else:
                # Make sure this is the same client
                details = self.clients[bot]

                if details["addr"] != websocket.remote_address[0]:
                    await self.error(websocket, f"Connected from incorrect IP")
                    await websocket.close()
                    return

                # Check the action
                if action not in self.actions:
                    await self.error(websocket, f"Invalid action: '{action}'")
                    continue

                act = self.actions[action]

                if "permission" in act:
                    if self.config.bots[bot]["permissions"].get(act["permission"]) != True:
                        await self.error(websocket, "Missing permissions")
                        continue

                # Call the action
                try:
                    result = await act["function"](websocket, bot, data)

                except:
                    traceback.print_exc()
                    await self.error(websocket, "Request failed")

    async def error(
            self,
            websocket,
            message
        ):

        await websocket.send(
            json.dumps(
                {
                    "success": False,
                    "error": message
                }
            )
        )

    async def send(
            self,
            websocket,
            data: dict = {}
        ):

        if len(data) > 0:
            data_ = {
                "data": data
            }

        else:
            data_ = {}

        await websocket.send(
            json.dumps(
                {
                    "success": True,
                    **data_
                }
            )
        )

    async def parse(
            self,
            websocket,
            message: str
        ) -> Tuple[str, dict]:

        data = json.loads(message)

        if "action" not in data:
            raise Exception("Missing action")

        action = data["action"].lower()

        if action not in self.actions:
            raise Exception(f"Invalid action: '{action}'")

        if "data" not in data:
            raise Exception("Missing data")

        return action, data["data"]

    async def auth(
            self,
            websocket,
            key: Optional[str]
        ) -> Tuple[bool, Optional[str]]:

        if key is None:
            return False, "Missing auth key"

        valid = False
        for name, details in self.config.bots.items():
            if details["key"] == key:
                valid = True
                break

        if not valid:
            return False, "Invalid key"

        if (
            websocket.remote_address[0] not in details["ips"]
            and "%" not in details["ips"]
        ):
            return False, f"Host {websocket.remote_address[0]} can't access this bot"

        return True, name