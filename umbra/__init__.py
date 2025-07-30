from brozzler.browser import Browser  # noqa F401
from umbra.controller import AmqpBrowserController
from importlib.metadata import version as _version
__version__ = _version('umbra')
Umbra = AmqpBrowserController

try:
    import os
    import sentry_sdk

    DEPLOYMENT_ENVIRONMENT = os.environ.get("DEPLOYMENT_ENVIRONMENT", "DEV")
    SENTRY_DSN = os.environ.get("SENTRY_DSN")

    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=DEPLOYMENT_ENVIRONMENT,
            release=__version__,
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0")),
        )
except ImportError:
    pass
