from brozzler.browser import Browser
from umbra.controller import AmqpBrowserController
from pkg_resources import get_distribution as _get_distribution
__version__ = _get_distribution('umbra').version
Umbra = AmqpBrowserController
