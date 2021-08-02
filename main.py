import ws

# Import actions
from ws import actions

ws.ws.actions = {
    "send_command": {
        "function": actions.control.send_command,
        "permission": "send_commands"
    },
    "auth": {}
}

ws.ws.start()