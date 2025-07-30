from brozzler.browser import Browser  # noqa F401
from umbra.controller import AmqpBrowserController
from importlib.metadata import version as _version
__version__ = _version('umbra')
Umbra = AmqpBrowserController
