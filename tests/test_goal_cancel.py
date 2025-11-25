from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from aiogram.types import ReplyKeyboardMarkup

from fatcules.handlers import goal_fat, goal_weight
from fatcules.keyboards import CANCEL


def make_message(text: str = CANCEL) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        from_user=SimpleNamespace(id=123),
        bot=SimpleNamespace(repo=None),
        message=None,
        answer=AsyncMock(),
    )


class DummyState:
    def __init__(self) -> None:
        self.clear = AsyncMock()


class GoalCancelTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_from_goal_weight_returns_to_main_menu(self) -> None:
        state = DummyState()
        message = make_message()

        await goal_weight(message, state)

        state.clear.assert_awaited_once()
        message.answer.assert_awaited_once()
        args, kwargs = message.answer.call_args
        self.assertEqual(args[0], "Cancelled. Choose next action.")
        self.assertIsInstance(kwargs.get("reply_markup"), ReplyKeyboardMarkup)

    async def test_cancel_from_goal_fat_returns_to_main_menu(self) -> None:
        state = DummyState()
        message = make_message()

        await goal_fat(message, state)

        state.clear.assert_awaited_once()
        message.answer.assert_awaited_once()
        args, kwargs = message.answer.call_args
        self.assertEqual(args[0], "Cancelled. Choose next action.")
        self.assertIsInstance(kwargs.get("reply_markup"), ReplyKeyboardMarkup)


if __name__ == "__main__":
    unittest.main()
