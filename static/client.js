var client_id = null;
var client_name = "";
var on_resize = null;
var devtest = false;
var admin = false;
var available_games = {};

/*
 * Toolkit
 */

// Repeat a string.
// From http://stackoverflow.com/a/202627/499515
String.prototype.repeat = function( num )
{
    return new Array( num + 1 ).join( this );
};


/*
 * Initialization and server communication
 */

$(window).on("beforeunload", function() {waiter.disconnect()});

$(document).ready(function() {
	client_id = parseInt(this.location.pathname.substring(6));
    if (client_id)
        devtest = true;

    chat.init();

	waiter.connect();

	$(window).on("resize", function() { chat.set_size(); if (on_resize) {on_resize();}});
});

function set_client_info(data) {
    client_id = data.id;
    client_name = data.name;
    loader.set_cache_control(data.cache_control);
    devtest = data.devtest;
    admin = data["admin"];
    if (admin) {
        loader.script("/static/admin.js");
    }
}

function set_games_info(params) {
    available_games = params["games"];
}

function quit(data) {
    if (data["reason"]) {
        alert("You have been disconnected: " + data["reason"]);
    }
// Todo: don't go to /, as this will now lead to reconnection.
//    window.location.href = "/";
}

var command_loop = (function() {
    var queue = [];
    var frozen = false;
    var in_iteration = false;

    var run_iteration = function() {
        if (frozen || in_iteration || queue.length == 0) {
            return
        }

        in_iteration = true;
        var message = queue.shift();
        var command = message["command"];
        var fn = eval(command);
        if (fn) {
            if (devtest)
                console.log("Running command: " + command);
            fn(message);
        } else {
            console.log("Unknown command: " + command);
        }
        in_iteration = false;
        run_iteration();
    };

    return {
        add: function(command) {
            queue.push(command);
            run_iteration();
        },
        add_several: function(commands) {
            queue = queue.concat(commands);
            run_iteration();
        },
        freeze: function() {
            frozen = true;
        },
        thaw: function() {
            frozen = false;
            run_iteration();
        }
    }
}());

var waiter = (function() {
    var request = null;

    var connect = function() {
        if (request) return;
        request = $.ajax({
            url: "/poll"+ (devtest? "/" + client_id : "") + "?session_id=" + session_id,
            dataType: "json",
            success: waitcomplete,
            cache: false,
        })
            .fail(function(jqXHR, textStatus, errorThrown) {
                if(jqXHR.status == 504) {
                    request = null;
                    connect();
                }
            });
    };

    var waitcomplete = function(commands) {
        request = null;
        command_loop.add_several(commands);
        connect();
    };

    return {
        connect: connect,
        disconnect: function() {
            if (request) {
                request.abort();
            }
        }
    };
}());

function send_request(data) {
	$.ajax({
		type : "POST",
		url : "/request"+ (devtest? "/" + client_id : "") + "?session_id=" + session_id,
		data : JSON.stringify(data)
	});
}

function send_response(data) {
	$.ajax({
		type : "POST",
		url : "/response" + (devtest? "/" + client_id : "") + "?session_id=" + session_id,
		data : JSON.stringify(data)
	});
}

var loader = (function() {
    var loaded_css = [];
    var cache_control = null;
    var currently_loading = [];

    var do_ajax = function(location, datatype, callback) {
        command_loop.freeze();
        if (cache_control)
            location += "?_=" + cache_control;
        currently_loading.push(location);

        var a =  $.ajax(location, {
            dataType: datatype,
            cache: Boolean(cache_control)
        });
        if (callback)
            a.done(callback);
        a.always(function () {loading_done(location);});
        return a;
    };

    var loading_done = function(location) {
        for (var i = currently_loading.length; i--; i >= 0) {
            if (currently_loading[i] === location) {
                currently_loading.splice(i, 1);
                break;
            }
        }
        if (!loader.is_loading())
            command_loop.thaw();
    };

    return {
        is_loading: function() {
            return currently_loading.length > 0;
        },
        set_cache_control: function(control_string) {
            if (control_string)
                cache_control = control_string;
        },
        script: function(location, callback) {
            do_ajax(location, "script", callback);
        },
        json: function(location, callback) {
            do_ajax(location, "json", callback);
        },
        html: function(location, target, callback) {
            do_ajax(location, "html", function(data) {
                if (target)
                    target.html(data);
                if (callback)
                    callback();
            });
        },
        css: function(location) {
            if (loaded_css.indexOf(location) !== -1)
                return;
            loaded_css.push(location);
            if (cache_control)
                location += "?_" + cache_control;
            else
                location += "?_" + Math.random();

            $("<link />", {
                "rel": "stylesheet",
                "type": "text/css",
                "href": location,
                load: function() {
                    $(window).resize();
                }
            }).appendTo("head");
        },
    }
}());


/*
 * General UI
 */

function default_cancel_interactions(data) {
	$('[id^="interaction_"]').remove();
	scroll_to_bottom($("#interactions"));
}

var cancel_interactions = default_cancel_interactions;

function scroll_to_bottom(e) {
	e.scrollTop(e.prop("scrollHeight"));
}

ui = function () {
    var ask_for_input = function() {
        ui.title.notify_of_activity();
    };

    var say = function (params) {
        $("#interactions").append($("<span />", {html : params["message"]}));
        $("#interactions").append($("<br />"));
        scroll_to_bottom($("#interactions"));
    };

    var choice = function (params) {
        var div = $("<div />", {id : "interaction_" + params["id"]});

        if (params["question"]) {
            var q = $("<span />", {html: params["question"]});
            if (params["new_line_after_question"])
                q.append($("<br />"));
            else
                q.append("&nbsp;");

            if (params["leave_question"])
                $("#interactions").append(q);
            else
                div.append(q);
        }

        var answers = $("<span />", {"class" : "choices"});
        div.append(answers);
        for (var i=0; i < params["answers"].length; i++) {
            var a = $("<a />", {
                html : params["answers"][i],
                href : "#"});
            a.click(
                {id : params["id"], reply : i},
                function (event) {
                    send_response({id: event.data.id, value : event.data.reply});
                    $("#interaction_" + event.data.id).remove();
                    scroll_to_bottom($("#interactions"));
                    return false;
                }
            );
            answers.append(a);
            answers.append(" ");
        }

        $("#interactions").append(div);
        scroll_to_bottom($("#interactions"));
        ui.ask_for_input();
    };

    return {
        ask_for_input: ask_for_input,
        say: say,
        choice: choice,
        disable_form_field: function(id) {
            $("#"+id).prop("disabled", true);
            $('label[for="' + id + '"]').addClass("disabled");
        },
        enable_form_field: function(id) {
            $("#"+id).prop("disabled", false);
            $('label[for="' + id + '"]').removeClass("disabled");
        },
        empty_interactions: function() {
            $("#interactions").empty();
        }
    };
}();

ui.title = function() {
    var current_title = "";

    var set_title = function(title) {
        current_title = title;
        document.title = title;
    };

    var disable_highlight = function () {
        document.title = current_title;
        $(document).off("focus", disable_highlight);
    };

    var highlight = function() {
        if (! document.hasFocus()) {
            document.title = "(!) " + current_title;
            $(document).on("focus", disable_highlight);
        }
    };

    return {
        set : set_title,
        notify_of_activity : highlight,
    };
}();


/*
 * Log in / Welcome
 */

welcome = function () {
    var init = function(data) {
        loader.html("/static/welcome.html", $("#main"), function() {
            for (var game in data.games) {
                if (!data.games.hasOwnProperty(game))
                    continue;
                $('#game').append($("<option/>", {
                    value: game,
                    text: data.games[game],
                    selected: game === data.default_game,
                }));
                $('#name').val(data.name);
            }
            $('#login').on("click", function() {
                send_request({
                    command: "welcome.do_login",
                    name: $("#name").val(),
                    game: $("#game").val(),
                });
                return false;
            })
        });
    };

    var invalid_name = function(data) {
        $("#error").text(data.reason + " Please choose a different name.")
    };

    return {
        init: init,
        invalid_name: invalid_name,
    }
}();


/*
 * The chat
 */

chat = function() {
    // var tz_offset = new Date().getTimezoneOffset() * 60000;
    var enabled = false;
    var initialized = false;

    // send a chat message
    var send_message = function() {
        send_request({command : "chat.message", message : $("#chat_input").val()});
        $("#chat_input").val("");
    };

    var format_time = function(time) {
        var d = new Date(time*1000);
        var h = d.getHours();
        var m = d.getMinutes();
        if (m < 10)
            m = "0" + m;
        return h + ":" + m;
    };

    return {
        init : function() {
            if (initialized)
                return;
            $("#chat").append($('<div id="chat_messages" />'));
            $("#chat").append($('<form>', {
                submit : function() { send_message(); return false; },
                html : '<input type="text" id="chat_input" />'
            }));
            initialized = true;
            if (enabled)
                chat.enable();
            else
                chat.disable();
        },

        enable : function() {
            $("#chat").show();
            enabled = true;
        },

        disable : function() {
            $("#chat").hide();
            enabled = false;
        },

        // receive a chat message
        receive_message : function(params) {
            var line = $("<span />", {
                "class": "chat_message",
                html : ": " + params["message"],
            });
            line.prepend($("<span />", {
                "class" : "chat_user",
                text : params["sender"],
            }));
            line.prepend($("<span />", {
                "class" : "chat_time",
                text : "<" + format_time(params["time"]) + "> ",
            }));
            $("#chat_messages").append(line, $("<br />"));
            $("#chat_messages").scrollTop(line.offset().top);
        },

        // receive a system message
        system_message : function(json) {
            var line = $("<span />", {
                text : json.message,
                "class" : "system-message system-message_" + json.level
            });
            line.prepend($("<span />", {
                "class" : "chat_time",
                text : "<" + format_time(json.time) + "> "}));
            $("#chat_messages").append(line, $("<br />"));
            $("#chat_messages").scrollTop(line.offset().top);
        },

        set_size : function() {
            if (enabled) {
                $("#chat input").width($("#chat").width());
            }
        },
    };

}();


/*
 * The lobby
 */

lobby = function () {
    var populate_switcher = function () {
        $("#lobby_switcher").change(function() {
            send_request({command : "lobby.switch", to : $("#lobby_switcher_select").val()});
            return false;
        });
        $.each(available_games, function(identifier, name) {
            $("#lobby_switcher_select").append($("<option />", {
                value : identifier,
                text : name,
                selected : identifier == lobby.current,
            }));
        });

        // todo: Reenable quitting.
        // $("#lobby_quit").prop("href", "/quit/" + client_id);
    };
/*
    var on_about_click = function() {
        $("#about_div").show().html(games[current_game].lobby.about_text);
        $("#about_div a").attr("target", "_blank");
        $("#about_div").append($("<button/>", {
            id: "about_box_close_button",
            text: "close",
            click: function() {$("#about_div").hide();}
        }));
    };
*/
    return {
        current: "",

        init: function (params) {
            lobby.current = params["this_lobby"];

            ui.title.set(available_games[lobby.current]);
            $("#main").removeClass().addClass("lobby");
            cancel_interactions = default_cancel_interactions;

            loader.html('/static/lobby.html', $("#main"), function () {
                $("#lobby_info_user").html(client_name);
                populate_switcher();
//                $("#about_button").on("click", on_about_click);
                $("#about_div").hide();

//                if (admin) {
//                    $("#lobby_switcher").append($("<button/>", {
//                        text: "admin",
//                        click: function () {
//                            send_request({"command": "go_to_admin"});
//                        }
//                    }))
//                }

                on_resize = lobby.set_size;
                $(window).resize();
            });
        },

        set_size: function () {
        },
    };
}();


/*
 * Games
 */
games = {};

games.lobby = function () {
	var min_players;
	var max_players;

	var create_player_cell = function(id, name) {
		var line = $("<span/>");
        line.append($('<input/>', {
            type : (min_players == 2 && max_players == 2 ? "radio" : "checkbox"),
            name : "players_radio",
            value : id,
            "id" : "players_radio_" + id,
            click : player_cell_clicked,
        }));
        line.append($("<label />", {
            "id" : "client_" + id,
            text : name,
            "for": "players_radio_" + id,
        }));
		return line;
	};

    var player_cell_clicked = function() {
        var num = $('input[name="players_radio"]:checked').length + 1;
        if (num < min_players || num > max_players) {
            $("#lobby_propose_button").prop('disabled', true);
        } else {
            $("#lobby_propose_button").prop('disabled', false);
        }
        if (games[lobby.current] && games[lobby.current].lobby && games[lobby.current].lobby.on_player_cell_clicked) {
            games[lobby.current].lobby.on_player_cell_clicked(num);
        }
    };

	var propose_game = function() {
		var players = $('input[name="players_radio"]:checked');
		var id_list = [];
		players.each( function() { id_list.push(parseInt($(this).val())) } );

        var options = {};
        $("#lobby_propose_options input:checkbox").each(
            function() {
                options[$(this).prop("name")] = $(this).prop("checked");
            }
        );

		send_request({command : "games.lobby.propose_game", players : id_list, options: options});
	};

	var layout = [];

	return {
		init : function(params) {
			min_players = params["min_players"];
			max_players = params["max_players"];

            loader.css("/static/" + params.this_game + "/game.css");
            // $("#automatch").hide();

            $("#lobby_propose_form").submit(function() {return false;});
            $("#lobby_propose_button").click(function() { propose_game(); return false; });
            if (min_players > 1) {
                $("#lobby_propose_button").prop('disabled', true);
            }

            layout = [];
            for (var p in params["clients"]) {
                if (!params["clients"].hasOwnProperty(p)) continue;
                if (p != client_id) {
                    games.lobby.client_joins({client_id : p, client_name : params["clients"][p]});
                }
            }

            /*
            loader.script("/static/" + params.this_game + "/game.js",
                function() {
                    if (games[current_game].lobby) {
                        lobby.game_lobby = games[current_game].lobby
                    } else {
                        lobby.game_lobby = {}
                    }
                    if (lobby.game_lobby.init) {
                        lobby.game_lobby.init();
                    }
                }
            );
            */
		},

		client_joins : function(params) {
			var added = false;
            var col, row;

			for (row = 0; row < layout.length; row++) {
				for (col = 0; col < layout[row].length; col++) {
					if (layout[row][col] == null) {
						layout[row][col] = params["client_id"];
						$("#lobby_player_table_" + row + "_" + col).append(
                            create_player_cell(params["client_id"], params["client_name"])
                        );
						added = true;
						break;
					}
				}
				if (added) break;
			}

			if (!added) {
				layout.push([null, null, null]);
				row = layout.length - 1;
				var tr = $("<tr />", {id : "lobby_player_table_" + row});
				for (col = 0; col < layout[row].length; col++) {
					tr.append($("<td />", {id : "lobby_player_table_" + row + "_" + col}));
				}
				$("#lobby_player_table").append(tr);
				$("#lobby_player_table_" + row + "_0").append(
                    create_player_cell(params["client_id"], params["client_name"])
                );
				layout[row][0] = params.client_id;
			}
		},

		client_leaves : function(params) {
			var found = false;
			for (var row = 0; row < layout.length; row++) {
				for (var col = 0; col < layout[row].length; col++) {
					if (layout[row][col] == params["client_id"]) {
						$("#lobby_player_table_" + row + "_" + col).empty();
						layout[row][col] = null;
						found = true;
						break;
					}
				}
				if (found) break;
			}
		},
	};
}();
/*
games.lobby.automatch = function() {

    var automatch_clicked = function() {
        if ($("#cb_automatch").prop("checked")) {
            var p = [];
            $('[id^="automatch_players_"]:checked').each(
                function() {p.push(parseInt($(this).val()))}
            );
            var options = {};
            if (lobby.game_lobby.get_automatch_options)
                options = lobby.game_lobby.get_automatch_options();
            send_request({
                "command": "lobby.automatch.enable",
                "players": p,
                "options": options,
            });
        } else {
            send_request({"command": "lobby.automatch.disable"})
        }
    };

    return {
        init : function(data) {
            $("#automatch").show();
            $("#cb_automatch").change(automatch_clicked);

            if (data.players.length > 1) {
                for (var i = 0; i < data.players.length; i++) {
                    var num = data.players[i];
                    $("#automatch_options").append($("<input/>", {
                        type: "checkbox",
                        id: "automatch_players_" + num,
                        value: num,
                        click: lobby.automatch.automatch_options_changed,
                    }));
                    $("#automatch_options").append($("<label/>", {
                        "for": "automatch_players_" + num,
                        id: "automatch_players_" + num + "_label",
                        text: num + " players"
                    }));
                }
                ui.disable_form_field("cb_automatch");
            }

            if (lobby.game_lobby.automatch_init) {
                lobby.game_lobby.automatch_init();
            }

        },

        automatch_options_changed : function() {
            if (lobby.game_lobby.on_automatch_options_changed)
                lobby.game_lobby.on_automatch_options_changed();
            if ($('[id^="automatch_players_"]').length > 0) {
                if ($('[id^="automatch_players_"]:checked').length == 0) {
                    $("#cb_automatch").prop("checked", false).change();
                    ui.disable_form_field("cb_automatch");
                } else {
                    ui.enable_form_field("cb_automatch");
                }
            }
            if ($("#cb_automatch").prop("checked")) {
                automatch_clicked();
            }
        },

        rerequest : automatch_clicked,
    };
}();
*/

/*
 * Base functions
 */
games.base = function() {
    var current_game = null;

    var display_end_message = function(json) {
        $("#interactions").empty();
        display_return_to_lobby_link();
        $("#interactions").append(" ");
        $("#interactions").append($("<a/>", {
            text : "See the full log.",
            href : json.log,
            target: "_blank"
        }));
        scroll_to_bottom($("#main"))
    };

    var display_return_to_lobby_link = function() {
        $("#interactions").append($("<a/>", {
            text : "Return to the lobby.",
            href : "#",
            click : function() {
                send_request({command : "game.leave"});
                return false;
            }
        }));
        scroll_to_bottom($("#main"))
    };

    var clicked_resign = false;
    var display_info = function(data) {
        /* This will show an info box with [content] and a resign button. */
        if ($("#info_box").length == 0) {
            $("#main").append($("<div />", {id: "info_box"}));
            $("#info_box").hide();
        }

        var info_box = $("#info_box");
        info_box.empty();
        var container = $("<div/>");
        games[current_game].populate_info_box(container, data);
        info_box.append(container)

        if (!games.base.resigned) {
            clicked_resign = false;
            info_box.append($("<button/>", {
                text: "Resign",
                id: "resign_button",
                click: function() {
                    if (clicked_resign) {
                        games.base.resign();
                        info_box.hide();
                    } else {
                        clicked_resign = true;
                        $(this).text("Resign?");
                        $(this).addClass("warning");
                    }
                }
            }));
        }

        info_box.append($("<button />", {
            text: "Close",
            id: "info_box_close_button",
            click: function() {
                $("#info_box").hide();
            }
        }));

        info_box.show();
    };

    var get_info_box_button = function() {
        /* Return a button that can show/hide the info box.*/
        return  $("<button />", {
            id: "info_button",
            text: "info",
            click: function() {
                if ($("#info_box").length > 0 && $("#info_box").is(":visible")) {
                    $("#info_box").hide();
                } else {
                    send_request({command: "games.get_info"});
                }
            }
        });
    };

    var show_waiting_message = function(command) {
        $("#interactions").append($("<span/>", {
            id: "waiting_message",
            html: command.message,
        }));
        scroll_to_bottom($("#main"));
    };

    var remove_waiting_message = function() {
        $("#waiting_message").remove();
        scroll_to_bottom($("#main"));
    };

    return {
        init: function(data) {
            loader.script("/static/" + data.game + "/game.js");
            loader.css("/static/" + data.game + "/game.css");
            games.base.resigned = data.resigned;
            ui.title.set(data.title);
            current_game = data.game;
        },

        resign: function() {
            send_request({"command": "game.resign"});
            cancel_interactions = function() {};
            $("#interactions").empty();
            display_return_to_lobby_link();
            games.base.resigned = true;
        },

        display_end_message: display_end_message,
        display_return_to_lobby_link: display_return_to_lobby_link,
        display_info: display_info,
        get_info_box_button: get_info_box_button,
        show_waiting_message: show_waiting_message,
        remove_waiting_message: remove_waiting_message,
    };
}();

games.base.cards = (function() {
    /*
     * We assume that the hand is displayed in div#hand and the individual cards are .card.
     */
    return {
        select: function(data) {
            cancel_interactions();
            games.tools.select_objects(
                data["prompt"],
                data["minimum"],
                data["maximum"],
                $("#hand .card"),
                function(selected) {
                    send_response({
						"id" : data.id,
						"choices" : selected.map(function () {return parseInt($(this).data("id"))}).toArray(),
					});
                }
            );
         },
    }
}());

games.base.dice = (function() {
    return {
        to_symbol: function(number) {
            return ["⚀","⚁","⚂","⚃","⚄","⚅"][number-1];
        }
    }
}());


/*
 * Game Tools
 */

games.tools = function() {
	var select_objects = function(prompt, min, max, objects, callback, filter) {
		if (min == max && min == 1) {
			select_one(prompt, objects, callback, filter);
            return;
        }
		if (typeof(filter) == "undefined") filter = function() {return true;};

		$("#interactions").append(prompt);
		$("#interactions").append($("<button />", {
			id : "done_button",
			disabled : min != 0,
			text : "Done",
			click : function () {
				var selected = objects.filter(".selected");
				objects.removeClass("selectable disabled selected unselected").off("click");
				$("#interactions").empty();
				callback(selected);
			},
		}));

		objects.not(filter).addClass("disabled");
		objects.filter(filter).addClass("selectable unselected").click(function () {
			$(this).toggleClass("unselected").toggleClass("selected");
			if (objects.filter(".selected").length >= min && objects.filter(".selected").length <= max)
				$("#done_button").prop("disabled", false);
			else
				$("#done_button").prop("disabled", true);
		});
        ui.ask_for_input();
	};

	var select_one = function(prompt, objects, callback, filter, choices) {
        /* Let the player select one object or an option from choices.
         *
         * prompt: Prompt the action with this string ("" or null to disable).
         * objects: A collection of jQuery DOM objects.
         * callback: Call this function when a player clicks on an object.
         *           The object is passed as parameter.
         * filter: This function is used to filter out a subset of the objects to make clickable.
         *         The rest will be marked .disabled. (Use $(this) to get the object.)
         * choices: Additional choices that the player can take. An array where each entry is a
         *          dictionary with entries [text] (displayed to the user) and [response] (sent
         *          to the server if selected).
         */
		if (typeof(filter) === "undefined") filter = function() {return true;};

        if (prompt)
    		$("#interactions").append(prompt);

        if (typeof(choices) !== "undefined") {
            if (prompt)
                $("#interactions").append($("<br/>"));
            var c = $("<span />", {"class" : "choices"});
            $("#interactions").append(c);
            for (var i=0; i < choices.length; i++) {
                var a = $("<a/>", {
                    html: choices[i].text,
                    href: "#",
                });
                a.click(choices[i].response, function(event) {
                    objects.removeClass("selectable disabled selected unselected").off("click");
                    $("#interactions").empty();
                    send_response(event.data);
                });
                c.append(a);
            }
        }

		objects.not(filter).addClass("disabled");
		objects.filter(filter).addClass("selectable").click(function () {
			objects.removeClass("selectable disabled selected unselected").off("click");
			$("#interactions").empty();
			callback($(this));
		});
        ui.ask_for_input();
	};

	return {
		select_objects : select_objects,
		select_one : select_one,
	}
}();

/*
 * The default log functionality
 */

log = function() {
    var simultaneous = false;
    var simultaneous_counter = 0;

    var format_log_message = function(data) {
        // This function currently doesn't really do anything, but it might be useful in the future.
        return data.message;
    };

    var new_message = function(data) {
        var container = $("#log");
        if (simultaneous) {
            container = $("#log_simultaneous_" + simultaneous_counter + "_" + data.player);
        }

        container.append($("<span>", {
            "id": "log_entry_" + data.message_id,
            "html": format_log_message(data),
        }));
        container.append("\n");

        scroll_to_bottom($("#log"));
        scroll_to_bottom($("#main"));
    };

    var start_simultaneous = function(data) {
        simultaneous = true;
        simultaneous_counter++;
        for (var i in data.player_ids) {
            $("#log").append($("<div>", {
                "id": "log_simultaneous_" + simultaneous_counter + "_" + data.player_ids[i]
            }));
        }
    };

    var end_simultaneous = function(data) {
        simultaneous = false;
    };

    var replace_message = function(data) {
        $("#log_entry_" + data.message_id).html(format_log_message(data));
    };

    return {
        new_message : new_message,
        replace_message : replace_message,
        start_simultaneous: start_simultaneous,
        end_simultaneous: end_simultaneous,
    }
}();
