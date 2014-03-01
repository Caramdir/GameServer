import hashlib
import time
import os

from config import log_path
import base.tools


class LogEntry():
    """Base class for log entries."""

    def __init__(self):
        self.id = -1
        self.use_tmp_message = False
        self.indentation = 0
        self.player = None
        self.reason = None

    def get_message(self, player=None):
        """Get the message to show to player. If player is None, return the message for the final log."""
        raise NotImplementedError()

    def _decorate_message(self, message):
        """Add indentation and reason to the message."""
        message = ("... " * self.indentation) + message
        if self.reason:
            message += " [" + self.reason + "]"
        return message


class SimpleLogEntry(LogEntry):
    """The simplest possible LogEntry subclass"""
    def __init__(self, message, reason=None):
        super().__init__()
        self._message = message
        self.reason = reason

    def get_message(self, player=None):
        return self._decorate_message(self._message)


class GameLogEntry(SimpleLogEntry):
    """A log entry created by the game itself (i.e. general status information).

    This class is mainly kept around for backwards-compatibility and because we
    might do something interesting with it in the future.
    """
    pass


class PlayerLogEntry(LogEntry):
    """A log entry created by a player (this is the most common entry type)."""

    def __init__(self, message_self, message_other=None, message_final=None, message_other_tmp=None, reason=None):
        """Create the log entry

        :param message_self: The message to show to the originating players.
        :param message_other: The message to show to other players (same as above if None).
        :param message_final: The message to show in the final log (same as above if None).
        :param message_other_tmp: A temporary message to show to other players (until the real message can be revealed).
                                  Only used if not None.
        """
        super().__init__()
        self._message_self = message_self
        if message_other is None:
            self._message_other = message_self
        else:
            self._message_other = message_other
        if not message_other_tmp is None:
            self._message_other_tmp = message_other_tmp
            self.use_tmp_message = True
        if message_final is None:
            self._message_final = self._message_other
        else:
            self._message_final = message_final
        self.reason = reason

    def get_message(self, player=None):
        if player is None:
            msg = self._message_final
        elif player == self.player:
            msg = self._message_self
        else:
            if self.use_tmp_message:
                msg = self._message_other_tmp
            else:
                msg = self._message_other
        return self._decorate_message(msg)


class HeaderLogEntry(SimpleLogEntry):
    """A log entry for headlines (e.g. announcing the start of a turn)."""
    def __init__(self, message, level=1):
        super().__init__(message)
        self.level = level

    def get_message(self, player=None):
        return '<span class="header_{}">{}</span>'.format(self.level, super().get_message(player))


class Log:
    """A very basic log class."""

    def __init__(self, players):
        super().__init__()
        self.next_id = 0
        self.entries = []
        self.players = players
        [p.set_log(self) for p in self.players]

    def get_next_id(self):
        """Get the next entry id and increase the counter."""
        self.next_id += 1
        return self.next_id

    def add_entry(self, entry):
        """Add an entry to the log and send it to the clients.

        :type entry: games.base.log.LogEntry
        """
        if entry.id == -1:
            entry.id = self.get_next_id()
        self.entries.append(entry)
        for player in self.players:
            self.send_entry(player, entry)

    def add_paragraph(self):
        """Add a paragraph to the log."""
        self.add_entry(SimpleLogEntry(""))

    def send_entry(self, player, entry):
        """Send an entry to a clients.

        :param player: The player representing the client who should get sent the entry.
        :type player: AbstractPlayer
        :param entry: The entry being sent.
        :type entry: games.base.log.LogEntry
        """
        cmd = {
            "command": "log.new_message",
            "message_id": entry.id,
            "message": entry.get_message(player)
        }
        if hasattr(entry, "player") and not entry.player is None:
            cmd["player"] = entry.player.client.id
        player.client.send_message(cmd)

    def resend_entry_to_all(self, entry):
        """Resend and entry to all players and replace any previous message sent for that entry."""
        for player in self.players:
            player.client.send_message({
                "command": "log.replace_message",
                "message_id": entry.id,
                "message": entry.get_message(player),
                "indentation": entry.indentation,
                "reason": entry.reason
            })

    def resend(self, player):
        """Resend the whole log to a player. This is currently done in a very suboptimal way."""
        [self.send_entry(player, entry) for entry in self.entries]

    def show_hidden(self):
        """Replace all temporary messages by the real message."""
        for entry in self.entries:
            if entry.use_tmp_message:
                entry.use_tmp_message = False
                self.resend_entry_to_all(entry)

    def send_command_to_all(self, command):
        """Send a command to all players."""
        [player.client.send_message(command) for player in self.players]

    def render_to_file(self, player=None, game="", template="log.html"):
        """Render the log to a file.

        :param player: Write the log for this player (None to get the full log).
        :param game: Short identifier of the game. Used as prefix for the file name and as wrapping class in the html file.
        :return: name of the file where the log was stored.
        :rtype : str
        """
        filename = game + "_" + hashlib.sha1(str(time.clock()).encode()).hexdigest() + ".html"
        entries = "\n".join([entry.get_message(player) for entry in self.entries])
        t = base.tools.template_loader.load(template)
        with open(os.path.join(log_path, filename), 'wb') as file:
            file.write(t.generate(entries=entries, game=game))
        return filename


class TurnLog(Log):
    """A log that has sections for turns and phases."""

    def __init__(self, players):
        super().__init__(players)
        self.current_turn = 0
        self.current_phase = 0
        self.turn_head = "Turn {}"
        self.phase_head = "Phase {}"

    def new_turn(self, message=None):
        """Start a new turn (and reset the phase counter to 0).

        :param message: Headline that is displayed in the log to announce the start of the new turn. Will format()'ed
                        with the current turn number. If message is None, the default will be used.
        """
        self.current_turn += 1
        self.current_phase = 0
        if message is None:
            self.add_entry(HeaderLogEntry(self.turn_head.format(self.current_turn), level=1))
        else:
            self.add_entry(HeaderLogEntry(message.format(self.current_turn), level=1))

    def new_phase(self, message=None):
        """Start a new phase.

        :param message: Headline that is displayed in the log to announce the start of the new phase. Will format()'ed
                        with the current phase number. If message is None, the default will be used.
        """
        self.current_phase += 1
        if message is None:
            self.add_entry(HeaderLogEntry(self.phase_head.format(self.current_phase), level=2))
        else:
            self.add_entry(HeaderLogEntry(message.format(self.current_phase), level=2))


class SimultaneousLog(TurnLog):
    """A log for games with simultaneous player actions."""

    def __init__(self, players):
        super().__init__(players)
        self.simultaneous = False

    def start_simultaneous(self):
        """Start a section where players can do simultaneous actions. Entries are sorted by player."""
        if self.simultaneous:
            return
        self.simultaneous = True
        self.simultaneous_entries = {player: [] for player in self.players}
        self.send_command_to_all({
            "command": "log.start_simultaneous",
            "player_ids": [p.client.id for p in self.players]
        })

    def end_simultaneous(self):
        """End a section where players can do simultaneous actions. Linearize the entries for the final log."""
        if not self.simultaneous:
            return
        self.simultaneous = False
        self.entries.extend([entry for player in self.players for entry in self.simultaneous_entries[player]])
        del self.simultaneous_entries
        self.send_command_to_all({"command": "log.end_simultaneous"})

    def add_entry(self, entry):
        if self.simultaneous:
            assert isinstance(entry, PlayerLogEntry), "Simultaneous log entries must come from players"
            if entry.id == -1:
                entry.id = self.get_next_id()
            self.simultaneous_entries[entry.player].append(entry)
            [self.send_entry(player, entry) for player in self.players]
        else:
            super().add_entry(entry)

    def new_turn(self, message=None):
        self.end_simultaneous()
        super().new_turn(message)

    def new_phase(self, message=None):
        self.end_simultaneous()
        super().new_phase(message)

    def show_hidden(self):
        super().show_hidden()
        if self.simultaneous:
            for p in self.simultaneous_entries:
                for entry in self.simultaneous_entries[p]:
                    if entry.use_tmp_message:
                        entry.use_tmp_message = False
                        self.resend_entry_to_all(entry)

    def resend(self, player):
        super().resend(player)
        if self.simultaneous:
            player.client.send_message({
                "command": "log.start_simultaneous",
                "player_ids": [p.client.id for p in self.players]}
            )
            [self.send_entry(player, entry) for p in self.simultaneous_entries for entry in self.simultaneous_entries[p]]


class PlayerLogFacade:
    """A facade for the logs for simpler access in player objects."""

    def __init__(self, main_log, player):
        """Initialize the facade

        :param main_log: The actual Log where the messages go.
        :type main_log: Log
        :param player: The player for which this facade is set up.
        :type player: AbstractPlayer
        """
        self.player = player
        self.log = main_log
        self.indentation = 0

    def add_entry(self, entry):
        """Add an entry to the log."""
        entry.player = self.player
        entry.indentation = self.indentation
        self.log.add_entry(entry)

    def simple_add_entry(self, message, message_other_tmp=None, reason=None):
        """Create and add a log entry with a message with only simple substitutions for the various versions.

        :param message: The message string. {player} is replaced by "You" or the player name and {s}
                        is replaced so that a grammatically correct sentence ensues.
        :param message_other_tmp: A temporary message to show to other players (until the real message can be revealed).
                                  Only used if not None.
        """
        if message_other_tmp is None:
            self.add_entry(PlayerLogEntry(
                message.format(Player="You", player="you", s="", es="", has="have"),
                message.format(Player=self.player.html, player=self.player.html, s="s", es="es", has="has"),
                reason=reason
            ))
        else:
            self.add_entry(PlayerLogEntry(
                message.format(Player="You", player="you", s="", es="", has="have"),
                message.format(Player=self.player.html, player=self.player.html, s="s", es="es", has="has"),
                message_other_tmp=message_other_tmp.format(Player=self.player.html, player=self.player.html, s="s", es="es", has="has"),
                reason=reason
            ))

    def indent(self):
        """Increase indentation of log messages."""
        self.indentation += 1

    def unindent(self):
        """Decrease indentation of log messages."""
        self.indentation -= 1
