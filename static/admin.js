admin = function() {
    return {
        init: function (data) {
            ui.title.set("Admin");
            loader.html("/static/admin.html", $('#main'),
                function() {
                    data["games"]["admin"] = "Admin";
                    lobby.populate_switcher(data["games"]);
                    $("#lobby_switcher_select").val("admin")

                    $("#send_system_message").on("click", function() {
                        send_request({
                            "command": "admin.send_system_message",
                            "message": $("#system_message").val()});
                        $("#system_message").val("");
                        return false;
                    });

                    data["running_games"].forEach(function(game) {
                        $("#running_games").append($("<li/>", {html: game["game"] + ": " + game["players"].join(", ")}));
                    });

                    data["empty_locations"].forEach(function(location) {
                        $("empty_locations").append($("<li/>", {html: location}));
                    });

                    $(window).resize();
            });
        },
    }
}();
