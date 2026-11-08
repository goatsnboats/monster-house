"""Tests for the debug tool's logic that don't need a broker."""

import socket

import pytest

from shared import mqtt_tool, topics


def test_short_names_resolve_to_topics():
    assert mqtt_tool.resolve_topic("blink") == topics.EYES_BLINK
    assert mqtt_tool.resolve_topic("monster") == topics.MONSTER_ALL


def test_full_topics_pass_through():
    full = topics.radar_target(2, "y")
    assert mqtt_tool.resolve_topic(full) == full


def test_unknown_short_name_is_an_error():
    with pytest.raises(SystemExit):
        mqtt_tool.resolve_topic("blnik")


def test_cannot_publish_to_a_pattern():
    with pytest.raises(SystemExit):
        mqtt_tool.main(["pub", "monster", "x"])


def test_topics_command_lists_every_alias(capsys):
    assert mqtt_tool.main(["topics"]) == 0
    out = capsys.readouterr().out
    for name, topic in topics.ALIASES.items():
        assert name in out and topic in out


def closed_port() -> int:
    """A local port with nothing listening on it."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_friendly_message_when_broker_is_down(capsys):
    code = mqtt_tool.main(["--port", str(closed_port()), "pub", "test", "x"])
    assert code == 2
    assert "Is it running?" in capsys.readouterr().err
