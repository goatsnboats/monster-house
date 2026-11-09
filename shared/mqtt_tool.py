"""Command-line MQTT debug tool for Monster House.

Examples (run from the repository root):

    python -m shared.mqtt_tool topics                 # list topic short names
    python -m shared.mqtt_tool sub                    # print everything under monster/
    python -m shared.mqtt_tool sub eye-status radar   # several topics at once
    python -m shared.mqtt_tool pub test '{"hello": 1}'
    python -m shared.mqtt_tool pub blink '{"ms": 180}'

TOPIC can be a short name from `topics` or a full topic (anything with a "/").
Payloads are sent exactly as typed; their formats aren't defined yet (TBD-003).
"""

from __future__ import annotations

import argparse
import sys
import threading

import paho.mqtt.client as mqtt

from shared import topics
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT, BrokerUnreachable, connect, new_client


def resolve_topic(name: str) -> str:
    """Turn a short name ('blink') into its topic; pass full topics through unchanged."""
    if name in topics.ALIASES:
        return topics.ALIASES[name]
    if "/" in name:
        return name
    raise SystemExit(f"Unknown topic name {name!r}. Run 'topics' to see the short names.")


def cmd_topics(_args: argparse.Namespace) -> int:
    width = max(len(name) for name in topics.ALIASES)
    for name, topic in topics.ALIASES.items():
        print(f"{name:<{width}}  {topic}")
    return 0


def cmd_pub(args: argparse.Namespace) -> int:
    topic = resolve_topic(args.topic)
    if topics.is_pattern(topic):
        raise SystemExit(f"Can't publish to a wildcard pattern: {topic}")

    client = new_client("mqtt-tool-pub")
    connect(client, args.host, args.port)
    client.loop_start()
    try:
        info = client.publish(topic, args.payload, qos=args.qos, retain=args.retain)
        info.wait_for_publish(timeout=5)
        if not info.is_published():
            print(f"Message to {topic} was not confirmed by the broker.", file=sys.stderr)
            return 1
    finally:
        client.disconnect()
        client.loop_stop()
    print(f"sent  {topic}  {args.payload}", file=sys.stderr)
    return 0


def cmd_sub(args: argparse.Namespace) -> int:
    wanted = [resolve_topic(t) for t in (args.topics or ["monster"])]
    received = 0
    done = threading.Event()

    def on_connect(client, _userdata, _flags, reason_code, _properties):
        if reason_code.is_failure:
            print(f"Broker refused the connection: {reason_code}", file=sys.stderr)
            done.set()
            return
        # (Re)subscribe on every connect, so a broker restart doesn't lose us.
        client.subscribe([(t, args.qos) for t in wanted])

    def on_subscribe(_client, _userdata, _mid, _reason_codes, _properties):
        # Tests wait for this line before publishing, so keep its wording.
        print(f"subscribed: {' '.join(wanted)}", file=sys.stderr, flush=True)

    def on_message(_client, _userdata, msg: mqtt.MQTTMessage):
        nonlocal received
        payload = msg.payload.decode("utf-8", errors="replace")
        flag = "  (retained)" if msg.retain else ""
        print(f"{msg.topic} {payload}{flag}", flush=True)
        received += 1
        if args.count and received >= args.count:
            done.set()

    client = new_client("mqtt-tool-sub")
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    connect(client, args.host, args.port)
    client.loop_start()
    try:
        finished = done.wait(timeout=args.timeout)  # timeout=None waits until Ctrl+C or --count
    except KeyboardInterrupt:
        finished = True
    finally:
        client.disconnect()
        client.loop_stop()

    if not finished:
        print(f"Timed out after {args.timeout} s with {received} message(s).", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m shared.mqtt_tool",
        description="Publish and subscribe to Monster House MQTT topics, for debugging.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"broker host (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"broker port (default {DEFAULT_PORT})")
    sub = parser.add_subparsers(dest="command", required=True)

    p_topics = sub.add_parser("topics", help="list topic short names")
    p_topics.set_defaults(func=cmd_topics)

    p_pub = sub.add_parser("pub", help="publish one message")
    p_pub.add_argument("topic", help="short name or full topic")
    p_pub.add_argument("payload", help="message text, e.g. a JSON string")
    p_pub.add_argument("--retain", action="store_true", help="ask the broker to keep it for new subscribers")
    p_pub.add_argument("--qos", type=int, choices=(0, 1, 2), default=1)
    p_pub.set_defaults(func=cmd_pub)

    p_sub = sub.add_parser("sub", help="print messages as they arrive (Ctrl+C to stop)")
    p_sub.add_argument("topics", nargs="*", help="short names or full topics (default: monster)")
    p_sub.add_argument("--count", type=int, default=0, help="stop after this many messages")
    p_sub.add_argument("--timeout", type=float, default=None, help="give up after this many seconds")
    p_sub.add_argument("--qos", type=int, choices=(0, 1, 2), default=1)
    p_sub.set_defaults(func=cmd_sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BrokerUnreachable as err:
        print(err, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
