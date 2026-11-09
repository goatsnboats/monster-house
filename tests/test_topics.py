"""Tests for shared/topics.py: the one list of MQTT topic names."""

from pathlib import Path

import pytest
from paho.mqtt.client import topic_matches_sub

from shared import topics

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every fixed topic a component publishes on (no wildcards allowed).
PUBLISH_TOPICS = [
    topics.EYES_LOOK,
    topics.EYES_EXPRESSION,
    topics.EYES_BLINK,
    topics.THEME,
    topics.EYES_LEFT_STATUS,
    topics.EYES_RIGHT_STATUS,
    topics.STATE,
    topics.RADAR_STATUS,
    topics.RADAR_TARGET_COUNT,
    topics.DEBUG_TEST,
]


def test_architecture_topic_names():
    # Spelled out once more here on purpose: these are the names in
    # docs/architecture.md §2 and §3c, and changing one is a message-format change.
    assert topics.EYES_LOOK == "monster/eyes/look"
    assert topics.EYES_EXPRESSION == "monster/eyes/expression"
    assert topics.EYES_BLINK == "monster/eyes/blink"
    assert topics.THEME == "monster/theme"
    assert topics.STATE == "monster/state"
    assert topics.EYES_LEFT_STATUS == "monster/eyes/left/status"
    assert topics.EYES_RIGHT_STATUS == "monster/eyes/right/status"
    assert topics.radar_target(1, "x") == "monster-radar/sensor/target_1_x/state"
    assert (
        topics.fpp_playlist_start("greet_01")
        == "falcon/player/FPP/set/playlist/greet_01/start"
    )


@pytest.mark.parametrize("topic", PUBLISH_TOPICS)
def test_publish_topics_are_well_formed(topic):
    assert topic, "empty topic"
    assert not topics.is_pattern(topic), "wildcards are for subscribing only"
    assert not topic.startswith("/") and not topic.endswith("/")
    assert "//" not in topic
    assert " " not in topic


def test_publish_topics_are_unique():
    assert len(PUBLISH_TOPICS) == len(set(PUBLISH_TOPICS))


def test_eye_status_per_side():
    assert topics.eye_status("left") == topics.EYES_LEFT_STATUS
    assert topics.eye_status("right") == topics.EYES_RIGHT_STATUS
    with pytest.raises(ValueError):
        topics.eye_status("middle")


def test_radar_target_topics():
    all_topics = {
        topics.radar_target(n, field)
        for n in range(1, topics.RADAR_MAX_TARGETS + 1)
        for field in topics.RADAR_TARGET_FIELDS
    }
    assert len(all_topics) == 3 * 3
    with pytest.raises(ValueError):
        topics.radar_target(0, "x")
    with pytest.raises(ValueError):
        topics.radar_target(4, "x")
    with pytest.raises(ValueError):
        topics.radar_target(1, "z")


@pytest.mark.parametrize("bad", ["", "a/b", "a+", "a#"])
def test_fpp_playlist_rejects_bad_names(bad):
    with pytest.raises(ValueError):
        topics.fpp_playlist_start(bad)


@pytest.mark.parametrize(
    ("pattern", "topic"),
    [
        (topics.EYES_STATUS_ALL, topics.EYES_LEFT_STATUS),
        (topics.EYES_STATUS_ALL, topics.EYES_RIGHT_STATUS),
        (topics.RADAR_SENSOR_ALL, topics.radar_target(2, "speed")),
        (topics.RADAR_SENSOR_ALL, topics.RADAR_TARGET_COUNT),
        (topics.FPP_ALL, topics.fpp_playlist_start("yawn")),
        (topics.MONSTER_ALL, topics.EYES_LOOK),
        (topics.MONSTER_ALL, topics.STATE),
        (topics.MONSTER_ALL, topics.DEBUG_TEST),
    ],
)
def test_subscribe_patterns_match(pattern, topic):
    assert topics.is_pattern(pattern)
    assert topic_matches_sub(pattern, topic)


def test_eye_status_pattern_does_not_catch_commands():
    assert not topic_matches_sub(topics.EYES_STATUS_ALL, topics.EYES_LOOK)


def test_aliases_point_at_known_topics():
    for name, topic in topics.ALIASES.items():
        assert "/" not in name, f"alias {name!r} would look like a topic"
        assert topic.startswith(("monster", topics.FPP_PREFIX)), topic


def test_no_hard_coded_topics_outside_shared():
    """Architecture rule: topic strings live in shared/topics.py and nowhere else."""
    prefixes = ('"monster/', "'monster/", '"monster-radar/', "'monster-radar/",
                '"falcon/player', "'falcon/player")
    allowed = {REPO_ROOT / "shared" / "topics.py", Path(__file__).resolve()}
    offenders = []
    for path in REPO_ROOT.rglob("*.py"):
        if ".venv" in path.parts or path.resolve() in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if any(p in text for p in prefixes):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"hard-coded MQTT topics in: {offenders}"
