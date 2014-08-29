# import json
import logging

import tornado.ioloop
import tornado.web
# import tornado.auth
# import tornado.gen

# Parse options and load configuration.
import config
# # Set up the log
# # noinspection PyUnresolvedReferences
# import base.log
import base.client
# import base.locations
#
logger = logging.getLogger(__name__)


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        """Return the client object for the current connection.

        Normally we identify the client by a (secure) cookie, but in DEVTEST instances we
        just append the client id to the URL so that several connections can be opened
        simultaneously.

        :return: Client object for the current connection.
        :rtype : base.client.Client
        """
        try:
#             if config.DEVTEST:
#                 identifier = self.request.path.split("/")[-1]
#             else:
            identifier = self.get_secure_cookie("client_id")
            return get_instance().clients[int(identifier)]
        except (KeyError, ValueError, TypeError):
            return None

#     def redirect_if_logged_in(self):
#         if self.current_user:
#             self.redirect("/play")
#             return True
#         return False
#
#
# class MainHandler(BaseHandler):
#     """Show the main interface."""
#     @tornado.web.authenticated
#     def get(self):
#         self.render("client.html", client=self.current_user, devtest=config.DEVTEST)
#
#
# class WaitHandler(BaseHandler):
#     """The long polling URI where we wait for new messages."""
#     @tornado.web.authenticated
#     @tornado.web.asynchronous
#     def get(self):
#         self.current_user.messages.wait_for_messages(self.on_new_messages)
#
#     def on_new_messages(self, disconnect=False):
#         if self.request.connection.stream.closed():
#             return
#         if disconnect:
#             self.finish(json.dumps([{"command": "quit", "reason": "Connected in different window."}]).encode())
#             return
#         self.set_header("Content-Type", "application/json")
#         msgs = self.current_user.messages.get_all()
#         self.finish(json.dumps(msgs).encode())
#
#
# class ClientRequestHandler(BaseHandler):
#     """The client sends a request."""
#     @tornado.web.authenticated
#     def post(self):
#         try:
#             request = json.loads(self.request.body.decode())
#             if logger.isEnabledFor(logging.DEBUG):
#                 logger.debug("Got request: {}.".format(request))
#             self.current_user.handle_request(request)
#             self.set_status(202)
#             self.write("OK")
#         except Exception as e:
#             self.current_user.notify_of_exception(e)
#             raise
#         finally:
#             base.client.send_all_messages()
#
#
# class ClientResponseHandler(BaseHandler):
#     """The client sends a response."""
#     @tornado.web.authenticated
#     def post(self):
#         try:
#             response = json.loads(self.request.body.decode())
#             if logger.isEnabledFor(logging.DEBUG):
#                 logger.debug("Got response: {}.".format(response))
#             self.current_user.post_response(response)
#             self.set_status(202)
#             self.write("OK")
#         except Exception as e:
#             self.current_user.notify_of_exception(e)
#             raise
#         finally:
#             base.client.send_all_messages()


class StartHandler(BaseHandler):
    """
    This is the entry point to the application.

    We either redirect to the login page or display the game area.
    """
    @tornado.web.authenticated
    def get(self):
        # if config.access_code:
        #     if not self.get_secure_cookie("access_code") or self.get_secure_cookie("access_code").decode() != config.access_code:
        #         self.render("access_code_form.html", wrong_code=False)
        #         return
        # if config.disable_stored_logins:
        #     self.redirect("/login/local")
        #     return
        self.render("client.html",
                    client=self.current_user,
                    #devtest=config.DEVTEST,
                    devtest=False,
                    )


class LoginHandler(BaseHandler):
    def get(self, auth_service=None):
        self.render("login.html", disable_stored_logins=config.disable_stored_logins, error=None)

    def post(self, auth_service=None):
        name = self.get_body_argument("name", default="", strip=True)

        if not name:
            self.render("login.html",
                        disable_stored_logins=config.disable_stored_logins,
                        error="You must enter a name.")
            return

        try:
            client = get_instance().clients.new(name)
        except base.client.DuplicateClientNameError:
            self.render("login.html",
                        disable_stored_logins=config.disable_stored_logins,
                        error="There is already a player with this name.")
            return

#        if config.DEVTEST:
#            self.redirect("/" + str(c.id))
#        else:
        self.set_secure_cookie("client_id", str(client.id))
        self.redirect("/")


# class AccessCodeHandler(BaseHandler):
#     """Checks whether a given access code was correct and then sets the cookie."""
#     # todo: Also check the access code when going directly to /login/{local,google}
#     def post(self, *args, **kwargs):
#         if self.get_argument("access_code") == config.access_code:
#             self.set_secure_cookie("access_code", config.access_code)
#             self.redirect("/")
#         else:
#             self.render("access_code_form.html", wrong_code=True)
#
#
# class BaseLoginHandler(BaseHandler):
#     """Base class for login handlers."""
#
#     def disconnect_existing_client(self):
#         """Disconnect any already existing client from the same browser."""
#         if self.current_user:
#             self.current_user.quit("You logged in again in a different window.")
#
#     def redirect_to_welcome(self, c):
#         c.move_to(base.locations.welcome_location)
#         self.redirect_to_play(c)
#
#     def redirect_to_play(self, c):
#         if config.DEVTEST:
#             self.redirect("/play/" + str(c.id))
#         else:
#             self.set_secure_cookie("client_id", str(c.id))
#             self.redirect("/play/")
#
#
# class UnregisteredLoginHandler(BaseLoginHandler):
#     """Logging in without registering."""
#     def get(self):
#         self.disconnect_existing_client()
#         c = base.client.Client()
#         if config.DEVTEST and config.devtest_direct_login:
#             c.move_to(config.GAMES[config.default_game]["lobby"])
#             self.redirect_to_play(c)
#         else:
#             self.redirect_to_welcome(c)
#
#
# class GoogleLoginHandler(BaseLoginHandler, tornado.auth.GoogleMixin):
#     """Logging in via Google."""
#     @tornado.web.asynchronous
#     @tornado.gen.coroutine
#     def get(self):
#         if config.disable_stored_logins:
#             self.redirect('/')
#             return
#         if self.get_argument("openid.mode", None):
#             user = yield self.get_authenticated_user()
#             self.disconnect_existing_client()
#             c = base.client.registration_handler.get_client(user["claimed_id"])
#             try:
#                 if not c.name:
#                     c.name = user["name"]
#             except base.client.InvalidClientNameError:
#                 pass
#             self.redirect_to_welcome(c)
#         else:
#             yield self.authenticate_redirect()
#
#
# class QuitHandler(BaseHandler):
#     @tornado.web.authenticated
#     def get(self):
#         self.current_user.quit()
#         self.redirect("/")
#
#
_application = tornado.web.Application(
    [
#         (r"/wait.*", WaitHandler),
#         (r"/request.*", ClientRequestHandler),
#         (r"/response.*", ClientResponseHandler),
        (r"/[0-9]*", StartHandler),
#         (r"/set_access_code", AccessCodeHandler),
        (r"/login(.*)", LoginHandler),
#         (r"/login/local", UnregisteredLoginHandler),
#         (r"/login/google", GoogleLoginHandler),
#         (r"/quit.*", QuitHandler),
    ],
    login_url="/login",
    template_path=config.template_path,
#     static_path=config.static_path,
    cookie_secret=config.cookie_secret,
    xheaders=True,
)
_application.listen(config.port)


class Server:
    """Control the application server and store state information."""
    def __init__(self, tornado_app=None):
        self.started = False
        self.clients = base.client.ClientManager()
#         self.locations = {}
#
        if tornado_app is None:
            tornado_app = _application
        self.app = tornado_app
#
#         self.sweeper = tornado.ioloop.PeriodicCallback(base.client.remove_inactive, 60000)

    def start(self):
        logger.debug("Starting the server.")
        self.started = True
#         self.sweeper.start()
        tornado.ioloop.IOLoop.instance().start()

    def stop(self):
        logger.debug("Stopping the server.")
        self.started = False
#         self.sweeper.stop()
        tornado.ioloop.IOLoop.instance().stop()

    def reset(self):
        if self.started:
            raise Exception("Cannot reset a running server.")

        self.clients = base.client.ClientManager()
#         self.locations = {}


_instance = None


def get_instance():
    global _instance

    if not _instance:
        _instance = Server()

    return _instance
