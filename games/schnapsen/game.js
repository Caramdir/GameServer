games.schnapsen = function() {

	return {
		
		init : function(data) {
			$("#main").empty();
            $("#main").removeClass().addClass("schnapsen");
            $("#main").append($("<div />", {id: "buttons"}));
            $("#buttons").append(games.base.get_info_box_button());
            $("#main").append($("<div />", {id : "play_area"}));
            $("#play_area").append($("<div />", {id: "deck"}));
            $("#play_area").append($("<div />", {id: "current_trick"}));
			$("#main").append($("<pre />", {id : "log"}));
			$("#main").append($("<div />", {id : "interactions"}));
			$("#main").append($("<div />", {id : "hand"}));
			on_resize = games.schnapsen.set_size;
			$(window).resize();
		},

		update_game_ui : function(data) {
            var deck = "";
            if (data.deck_size) {
                deck += '<span class="open-card">';
				if (data.open_card) {
					deck += data.open_card;
				} else {
					deck += '<span class="card">🂠</span>';
				}
                deck += "</span>";
                deck += '<span class="deck-card card">🂠</span>';
			}
			$("#deck").html(deck);
            $("#current_trick").finish();
            $("#current_trick").empty();
            $("#current_trick").show();
            for (var i=0; i<data.current_trick.length; i++) {
                $("#current_trick").append(data.current_trick[i]);
            }
            if (data.current_trick.length == 2) {
                $("#current_trick").fadeOut(5000);
            }
        },

        update_player_ui : function(json) {
			var h = $("#hand");
			h.empty();
			for (var i=0; i<json.hand.length; i++) {
				h.append($(json.hand[i]));
				h.append("&nbsp;");
			}
		},

        populate_info_box : function(container, data) {
            container.append("<strong>Trump:</strong> " + data["trump"] + "<br/>");
            container.append("<strong>Remaining cards:</strong> " + data["deck_size"]);
            container.append("<br/><br/>")
            container.append("<strong>Points:</strong> " + data["points"] + "<br/>");
            container.append("<strong>Taken cards: </strong> ");
            for (var i=0; i < data["taken_cards"].length; i++) {
                container.append(data["taken_cards"][i]);
            }
        },

		play_turn : function(data) {
            var i;
            var choices = [];
			for (i=0; i < data.options.length; i++) {
                var choice = {response: {id: data.id}};
                switch (data.options[i].type) {
                    case "exchange":
                        choice.text = "Exchange the trump jack for the open card.";
                        choice.response.type = "exchange";
                        break;
                    case "close":
                        choice.text = "Close the stock.";
                        choice.response.type = "close";
                        break;
                    case "marriage":
                        choice.text = "Play a marriage of " + data.options[i].suit_html + ".";
                        choice.response.type = "marriage";
                        choice.response.suit = data.options[i].suit;
                }
                choices.push(choice);
			}

            games.tools.select_one(
                null,
                $("#hand .card"),
                function (e) {
                    send_response({id: data.id, type: "card", card: e.attr("id")});
                },
                function () {
                    return data.cards.indexOf($(this).attr("id")) !== -1;
                },
                choices
            );
            scroll_to_bottom($("#main"));
		},

		set_size : function() {
            $("#main").height($(window).height() - $("#chat").outerHeight(true));
            $("#play_area").height($("#main").height() - $("#interactions").outerHeight(true) - $("#hand").outerHeight(true));
            $("#log").height($("#play_area").height());
            $("#log").outerWidth($("#main").width() - $("#play_area").outerWidth(true));
			scroll_to_bottom($("#main"));
		},
    };
}();

games.schnapsen.lobby = function() {
    return {
        about_text :
            '<p><a href="http://en.wikipedia.org/wiki/Schnapsen">Schnapsen</a> is traditional Austrian trick-taking card game.</p>' +
            '<a href="http://www.boardgamegeek.com/boardgame/11582/schnapsen">BBG entry</a>; <a href="http://www.pagat.com/marriage/schnaps.html">Rules</a>',
	};
}();
