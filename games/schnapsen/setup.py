import os
from config import static_path, template_path
from base.tools import ensure_symlink

static = os.path.join(static_path, "schnapsen")

# Create the directory for static files
if not os.path.isdir(static):
    os.makedirs(static)

# Create symlinks
ensure_symlink(os.path.join(os.path.dirname(__file__), "game.js"), os.path.join(static, "game.js"))
ensure_symlink(os.path.join(os.path.dirname(__file__), "game.css"), os.path.join(static, "game.css"))
ensure_symlink(os.path.join(os.path.dirname(__file__), "log.html"), os.path.join(template_path, "log_schnapsen.html"))