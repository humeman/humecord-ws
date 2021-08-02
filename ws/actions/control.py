"""
Humecord.WS: Control Actions

These actions allow for the remote control of bots in various manners.
"""

import ws

command_actions = {
    "reload": {
        "data": {
            "force": bool
        }
    },
    "shutdown": {
        "data": {}
    },
    "kill": {
        "data": {}
    },
    "command": {
        "data": {
            "command": str
        }
    }
}

async def send_command(
        websocket,
        bot: str,
        data: dict
    ):
    """
    Sends a control command to the specified list of bots.
    
    Data:
        bots (list[str]) - Bots to send command to
        action (str) - Action to execute (of below)
            reload [force: bool]
            shutdown
            kill
            command [command: str]
        data (dict) - Data to pass along, depending on action
    """

    # -- VALIDATE: Bots --
    # Find bot list
    if "bots" not in data:
        await ws.ws.error(websocket, "Missing bots")
        return

    bots = data["bots"]

    if type(bots) != list:
        await ws.ws.error(websocket, "Bots must be a list")
        return

    # Check if all bots exist
    for bot_ in bots:
        if bot_ not in ws.ws.config.bots:
            await ws.ws.error(websocket, f"Bot doesn't exist: '{bot_}'")
            return

    # -- VALIDATE: Action --
    if "action" not in data:
        await ws.ws.error(websocket, "Missing action")
        return

    action = data["action"]

    if action not in command_actions:
        await ws.ws.error(websocket, f"Invalid action: {action}")
        return

    act = command_actions[action]

    # -- VALIDATE: Data --
    if "data" in act:
        data_comp = {}

        if "data" not in data:
            await ws.ws.error(websocket, f"Action '{action}' requires data")
            return

        cdata = data["data"]

        for key, value in act['data'].items():
            if key not in cdata:
                await ws.ws.error(websocket, f"Missing data key: '{key}'")
                return

            if type(key) != value:
                await ws.ws.error(websocket, f"Key '{key}' is of wrong type")
                return

            # Append
            data_comp[key] = cdata[key]

    else:
        data_comp = {}

    # -- Send command --
    success = []
    fail = []

    for bot_ in bots:
        if bot_ not in ws.ws.clients:
            fail.append(bot_)
            continue

        b = ws.ws.clients[bot_]

        try:
            await ws.ws.send(
                b["socket"],
                {
                    "type": "action",
                    "action": "send_command",
                    "data": {
                        "action": action,
                        "data": data_comp
                    }
                }
            )

        except:
            fail.append(bot_)
        
        else:
            success.append(bot_)

    await ws.ws.send(
        websocket,
        {
            "type": "response",
            "action": "send_command",
            "data": {
                "success": success,
                "fail": fail
            }
        }
    )