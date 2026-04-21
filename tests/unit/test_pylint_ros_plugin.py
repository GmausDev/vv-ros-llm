from __future__ import annotations

import astroid
from pylint.lint import PyLinter
from pylint.testutils import CheckerTestCase, MessageTest

from vv_ros_llm.vv.pylint_ros_plugin import (
    BlockingCallInCallbackChecker,
    QosDepthChecker,
    RclpyLifecycleChecker,
    register,
)


class TestRclpyLifecycleChecker(CheckerTestCase):
    CHECKER_CLASS = RclpyLifecycleChecker

    def test_missing_all_three_lifecycle_messages(self):
        mod = astroid.parse("x = 1\n")
        self.walk(mod)
        with self.assertAddsMessages(
            MessageTest(msg_id="missing-rclpy-init", line=1),
            MessageTest(msg_id="missing-rclpy-shutdown", line=1),
            MessageTest(msg_id="missing-destroy-node", line=1),
            ignore_position=True,
        ):
            self.checker.close()

    def test_silent_when_all_present(self):
        code = """
import rclpy
def main():
    rclpy.init()
    node = object()
    node.destroy_node()
    rclpy.shutdown()
"""
        mod = astroid.parse(code)
        self.walk(mod)
        with self.assertNoMessages():
            self.checker.close()


class TestBlockingCallInCallbackChecker(CheckerTestCase):
    CHECKER_CLASS = BlockingCallInCallbackChecker

    def test_time_sleep_in_callback_is_flagged(self):
        code = """
import time
def on_timer_callback(self):
    time.sleep(1)
"""
        mod = astroid.parse(code)
        call = next(mod.nodes_of_class(astroid.Call))
        with self.assertAddsMessages(
            MessageTest(
                msg_id="blocking-in-callback",
                node=call,
                args=("time.sleep",),
            ),
            ignore_position=True,
        ):
            self.walk(mod)

    def test_time_sleep_outside_callback_not_flagged(self):
        code = """
import time
def helper():
    time.sleep(1)
"""
        mod = astroid.parse(code)
        with self.assertNoMessages():
            self.walk(mod)


class TestQosDepthChecker(CheckerTestCase):
    CHECKER_CLASS = QosDepthChecker

    def test_create_publisher_without_depth_is_flagged(self):
        code = "self.create_publisher(Msg, 't')"
        call = astroid.extract_node(code)
        with self.assertAddsMessages(
            MessageTest(msg_id="missing-qos-depth", node=call),
            ignore_position=True,
        ):
            self.checker.visit_call(call)

    def test_create_publisher_with_depth_kwarg_not_flagged(self):
        code = "self.create_publisher(Msg, 't', depth=10)"
        call = astroid.extract_node(code)
        with self.assertNoMessages():
            self.checker.visit_call(call)


def test_register_adds_three_checkers():
    linter = PyLinter()
    register(linter)
    names = {c.name for c in linter.get_checkers()}
    assert {
        "rclpy-lifecycle",
        "rclpy-blocking-callbacks",
        "rclpy-qos-depth",
    }.issubset(names)
