#!/usr/bin/env python

import argparse
import os
import sys
import logging
import socket
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

