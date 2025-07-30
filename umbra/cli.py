#!/usr/bin/env python

import argparse
import os
import sys
import logging
import pprint
import signal
import socket
import threading
import traceback
import time
import umbra
import json
from kombu import Connection, Exchange, Queue
from brozzler import suggest_default_chrome_exe

def browse_url():
    arg_parser = argparse.ArgumentParser(prog=os.path.basename(__file__),
            description='browse-url - open urls in chrome/chromium and run behaviors',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('urls', metavar='URL', nargs='+', help='URL(s) to browse')
    arg_parser.add_argument('--behavior-parameters', dest='behavior_parameters',
            default=None, help='json blob of parameters to use populate the javascript behavior template, e.g. {"parameter_username":"x","parameter_password":"y"}')
    arg_parser.add_argument(
            '--username', dest='username', default=None,
            help='use this username to try to log in if a login form is found')
    arg_parser.add_argument(
            '--password', dest='password', default=None,
            help='use this password to try to log in if a login form is found')
    arg_parser.add_argument('-w', '--browser-wait', dest='browser_wait', default='60',
            help='seconds to wait for browser initialization')
    arg_parser.add_argument('-e', '--executable', dest='chrome_exe',
            default=suggest_default_chrome_exe(),
            help='executable to use to invoke chrome')
    arg_parser.add_argument('-v', '--verbose', dest='log_level',
            action="store_const", default=logging.INFO, const=logging.DEBUG)
    arg_parser.add_argument('--version', action='version',
            version="umbra {} - {}".format(umbra.__version__, os.path.basename(__file__)))
    args = arg_parser.parse_args(args=sys.argv[1:])

    logging.basicConfig(stream=sys.stdout, level=args.log_level,
            format='%(asctime)s %(process)d %(levelname)s %(threadName)s %(name)s.%(funcName)s(%(filename)s:%(lineno)d) %(message)s')

    logger = logging.getLogger(__name__)

    behavior_parameters = None
    if args.behavior_parameters is not None:
        behavior_parameters = json.loads(args.behavior_parameters)

    with umbra.Browser(chrome_exe=args.chrome_exe) as browser:
        for url in args.urls:
            final_page_url, outlinks = browser.browse_page(
                    url, behavior_parameters=behavior_parameters,
                    username=args.username, password=args.password)
            logger.info('Outlinks Found:\n\t%s', '\n\t'.join(outlinks))


def drain_queue():
    arg_parser = argparse.ArgumentParser(prog=os.path.basename(__file__),
            description='drain-queue - consume messages from AMQP queue',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('-u', '--url', dest='amqp_url', default='amqp://guest:guest@localhost:5672/%2f',
            help='URL identifying the AMQP server to talk to')
    arg_parser.add_argument('--exchange', dest='amqp_exchange', default='umbra',
            help='AMQP exchange name')
    arg_parser.add_argument('--queue', dest='amqp_queue', default='urls',
            help='AMQP queue name')
    arg_parser.add_argument('-n', '--no-ack', dest='no_ack', action="store_const",
            default=False, const=True, help="leave messages on the queue (default: remove them from the queue)")
    arg_parser.add_argument('-r', '--run-forever', dest='run_forever', action="store_const",
            default=False, const=True, help="run forever, waiting for new messages to appear on the queue (default: exit when all messages in the queue have been consumed)")
    arg_parser.add_argument('-v', '--verbose', dest='log_level',
            action="store_const", default=logging.INFO, const=logging.DEBUG)
    arg_parser.add_argument('--version', action='version',
            version="umbra {} - {}".format(umbra.__version__, os.path.basename(__file__)))
    args = arg_parser.parse_args(args=sys.argv[1:])

    logging.basicConfig(stream=sys.stderr, level=args.log_level,
            format='%(asctime)s %(process)d %(levelname)s %(threadName)s %(name)s.%(funcName)s(%(filename)s:%(lineno)d) %(message)s')

    def print_and_maybe_ack(body, message):
        # do this instead of print(body) so that output syntax is json, not python
        # dict (they are similar but not identical)
        print(message.body)

        if not args.no_ack:
            message.ack()

    exchange = Exchange(args.amqp_exchange, 'direct', durable=True)
    queue = Queue(args.amqp_queue, exchange=exchange)
    try:
        with Connection(args.amqp_url) as conn:
            with conn.Consumer(queue, callbacks=[print_and_maybe_ack]) as consumer:
                consumer.qos(prefetch_count=1)
                while True:
                    try:
                        conn.drain_events(timeout=0.5)
                    except socket.timeout:
                        if not args.run_forever:
                            logging.debug("exiting, no messages left on the queue")
                            break
    except KeyboardInterrupt:
        logging.debug("exiting, stopped by user")


def queue_json():
    arg_parser = argparse.ArgumentParser(prog=os.path.basename(__file__),
            description='queue-json - send json message to umbra via AMQP',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('-u', '--url', dest='amqp_url', default='amqp://guest:guest@localhost:5672/%2f',
            help='URL identifying the AMQP server to talk to')
    arg_parser.add_argument('--exchange', dest='amqp_exchange', default='umbra',
            help='AMQP exchange name')
    arg_parser.add_argument('--routing-key', dest='amqp_routing_key', default='urls',
            help='AMQP routing key')
    arg_parser.add_argument('-v', '--verbose', dest='log_level',
            action="store_const", default=logging.INFO, const=logging.DEBUG)
    arg_parser.add_argument('--version', action='version',
            version="umbra {} - {}".format(umbra.__version__, os.path.basename(__file__)))
    arg_parser.add_argument('payload_json', metavar='JSON_PAYLOAD', help='json payload to send to umbra')
    args = arg_parser.parse_args(args=sys.argv[1:])

    logging.basicConfig(stream=sys.stdout, level=args.log_level,
            format='%(asctime)s %(process)d %(levelname)s %(threadName)s %(name)s.%(funcName)s(%(filename)s:%(lineno)d) %(message)s')

    payload = json.loads(args.payload_json)

    exchange = Exchange(args.amqp_exchange, 'direct', durable=True)
    with Connection(args.amqp_url) as conn:
        producer = conn.Producer(serializer='json')
        logging.info("sending to amqp url={} exchange={} routing_key={} -- {}".format(args.amqp_url, args.amqp_exchange, args.amqp_routing_key, payload))
        producer.publish(payload, routing_key=args.amqp_routing_key, exchange=exchange)


def queue_url():
    arg_parser = argparse.ArgumentParser(prog=os.path.basename(__file__),
            description='queue-url - send url to umbra via AMQP',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('-u', '--url', dest='amqp_url', default='amqp://guest:guest@localhost:5672/%2f',
            help='URL identifying the AMQP server to talk to')
    arg_parser.add_argument('--exchange', dest='amqp_exchange', default='umbra',
            help='AMQP exchange name')
    arg_parser.add_argument('--routing-key', dest='amqp_routing_key', default='urls',
            help='AMQP routing key')
    arg_parser.add_argument('-i', '--client-id', dest='client_id', default='load_url.0',
            help='client id - included in the json payload with each url; umbra uses this value as the routing key to send requests back to')
    arg_parser.add_argument('-v', '--verbose', dest='log_level',
            action="store_const", default=logging.INFO, const=logging.DEBUG)
    arg_parser.add_argument('--version', action='version',
            version="umbra {} - {}".format(umbra.__version__, os.path.basename(__file__)))
    arg_parser.add_argument('urls', metavar='URL', nargs='+', help='URLs to send to umbra')
    args = arg_parser.parse_args(args=sys.argv[1:])

    logging.basicConfig(stream=sys.stdout, level=args.log_level,
            format='%(asctime)s %(process)d %(levelname)s %(threadName)s %(name)s.%(funcName)s(%(filename)s:%(lineno)d) %(message)s')

    exchange = Exchange(args.amqp_exchange, 'direct', durable=True)
    with Connection(args.amqp_url) as conn:
        producer = conn.Producer(serializer='json')
        for url in args.urls:
            payload = {'url': url, 'metadata': {}, 'clientId': args.client_id}
            logging.info("sending to amqp url={} exchange={} routing_key={} -- {}".format(args.amqp_url, args.amqp_exchange, args.amqp_routing_key, payload))
            producer.publish(payload, routing_key=args.amqp_routing_key, exchange=exchange)


def run_umbra():
    arg_parser = argparse.ArgumentParser(prog=os.path.basename(__file__),
            description='umbra - browser automation tool communicating via AMQP',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('-e', '--executable', dest='chrome_exe',
            default=suggest_default_chrome_exe(),
            help='Executable to use to invoke chrome')
    arg_parser.add_argument('-u', '--url', dest='amqp_url', default='amqp://guest:guest@localhost:5672/%2f',
            help='URL identifying the amqp server to talk to')
    arg_parser.add_argument('--exchange', dest='amqp_exchange', default='umbra',
            help='AMQP exchange name')
    arg_parser.add_argument('--queue', dest='amqp_queue', default='urls',
            help='AMQP queue to consume urls from')
    arg_parser.add_argument('--routing-key', dest='amqp_routing_key', default='urls',
            help='AMQP routing key to assign to AMQP queue of urls')
    arg_parser.add_argument('-n', '--max-browsers', dest='max_browsers', default='1',
            help='Max number of chrome instances simultaneously browsing pages')
    arg_parser.add_argument('-v', '--verbose', dest='log_level',
            action="store_const", default=logging.INFO, const=logging.DEBUG)
    arg_parser.add_argument('--version', action='version',
            version="umbra {}".format(umbra.__version__))
    args = arg_parser.parse_args(args=sys.argv[1:])

    logging.basicConfig(stream=sys.stdout, level=args.log_level,
            format='%(asctime)s %(process)d %(levelname)s %(threadName)s %(name)s.%(funcName)s(%(filename)s:%(lineno)d) %(message)s')

    logging.info("umbra {} starting up".format(umbra.__version__))

    controller = umbra.Umbra(args.amqp_url, args.chrome_exe,
            max_active_browsers=int(args.max_browsers),
            exchange_name=args.amqp_exchange, queue_name=args.amqp_queue,
            routing_key=args.amqp_routing_key)

    def browserdump_str(pp, b):
        x = []
        x.append(pp.pformat(b.__dict__))
        # if b._chrome_instance:
        #     x.append("=> {} chrome instance:".format(b))
        #     x.append(pp.pformat(b._chrome_instance.__dict__))
        # if b._behavior:
        #     x.append("=> {} active behavior:".format(b))
        #     x.append(pp.pformat(b._behavior.__dict__))
        return "\n".join(x)

    def dump_state(signum, frame):
        pp = pprint.PrettyPrinter(indent=4)
        state_strs = []

        for th in threading.enumerate():
            state_strs.append(str(th))
            stack = traceback.format_stack(sys._current_frames()[th.ident])
            state_strs.append("".join(stack))

        state_strs.append("umbra controller:")
        state_strs.append(pp.pformat(controller.__dict__))
        state_strs.append("")

        for b in controller._browser_pool._in_use:
            state_strs.append("{} (in use):".format(b))
            state_strs.append(browserdump_str(pp, b))
            state_strs.append("")

        logging.warn("dumping state (caught signal {})\n{}".format(signum, "\n".join(state_strs)))


    class ShutdownRequested(Exception):
        pass

    def sigterm(signum, frame):
        raise ShutdownRequested('shutdown requested (caught SIGTERM)')
    def sigint(signum, frame):
        raise ShutdownRequested('shutdown requested (caught SIGINT)')

    signal.signal(signal.SIGQUIT, dump_state)
    signal.signal(signal.SIGHUP, controller.reconnect)
    signal.signal(signal.SIGTERM, sigterm)
    signal.signal(signal.SIGINT, sigint)

    controller.start()

    try:
        while True:
            time.sleep(0.5)
    except ShutdownRequested as e:
        logging.info(e)
    except BaseException as e:
        logging.fatal(e, exc_info=True)
    finally:
        controller.shutdown_now()
        for th in threading.enumerate():
            if th != threading.current_thread():
                th.join()
    logging.info("all finished, exiting")
