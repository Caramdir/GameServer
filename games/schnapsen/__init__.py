#from games.schnapsen import game
import base.lobby

INFO = {
    "name": "Schnapsen",
    "lobby": base.lobby.GameLobby("schnapsen", 2, 2)
#    "lobby": game.Lobby(),
}
