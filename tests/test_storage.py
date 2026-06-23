import uuid

import pytest
from nicegui import ui
from nicegui.testing import User

from beaverhabits import views
from beaverhabits.app.auth import user_authenticate, user_create
from beaverhabits.app.db import User as HabitUser
from beaverhabits.app.db import create_db_and_tables, engine
from beaverhabits.configs import StorageType, settings
from beaverhabits.utils import dummy_days

EMAIL = f"{uuid.uuid1()}@test.com"
PASSWORD = "test"


@pytest.fixture
async def habit_user():
    await create_db_and_tables()

    user = await user_authenticate(email=EMAIL, password=PASSWORD)
    if not user:
        user = await user_create(email=EMAIL, password=PASSWORD)
    yield user

    # close db connection after test
    await engine.dispose()


async def test_user_session(user: User):
    @ui.page("/")
    async def page():
        days = await dummy_days(5)
        habit_list = views.get_or_create_session_habit_list(days)
        assert habit_list is not None

    await user.open("/")


async def test_user_db(user: User, habit_user: HabitUser):
    settings.HABITS_STORAGE = StorageType.USER_DATABASE

    @ui.page("/")
    async def page():
        days = await dummy_days(5)
        habit_list = await views.get_or_create_user_habit_list(
            habit_user, views.dummy_habit_list(days)
        )
        assert habit_list is not None

        habit_list = await views.get_user_habit_list(habit_user)
        assert habit_list is not None

    await user.open("/")

    # close db connection after test

    await engine.dispose()


async def test_user_disk(user: User, habit_user: HabitUser):
    settings.HABITS_STORAGE = StorageType.USER_DISK

    @ui.page("/")
    async def page():
        days = await dummy_days(5)
        habit_list = await views.get_or_create_user_habit_list(
            habit_user, views.dummy_habit_list(days)
        )
        assert habit_list is not None

        habit_list = await views.get_user_habit_list(habit_user)
        assert habit_list is not None

    await user.open("/")
    # close db connection after test
    await engine.dispose()

# --- Tests for habit analytics (longest streak + completion rate) ---
import datetime
from beaverhabits.storage.dict import DictHabit


def _make_habit(days: list[datetime.date]) -> DictHabit:
    """Build a minimal habit ticked on the given days."""
    records = [{"day": d.strftime("%Y-%m-%d"), "done": True} for d in days]
    return DictHabit({"name": "Test Habit", "records": records}, None)


def test_longest_streak_consecutive():
    days = [datetime.date(2024, 1, 1), datetime.date(2024, 1, 2), datetime.date(2024, 1, 3)]
    assert _make_habit(days).longest_streak() == 3


def test_longest_streak_resets_on_gap():
    # Two in a row, a gap, then one more -> longest run is 2
    days = [datetime.date(2024, 1, 1), datetime.date(2024, 1, 2), datetime.date(2024, 1, 4)]
    assert _make_habit(days).longest_streak() == 2


def test_longest_streak_empty():
    assert _make_habit([]).longest_streak() == 0


def test_completion_rate():
    # 3 ticked days across a 4-day window -> 75.0%
    days = [datetime.date(2024, 1, 1), datetime.date(2024, 1, 2), datetime.date(2024, 1, 3)]
    rate = _make_habit(days).completion_rate(
        start=datetime.date(2024, 1, 1), end=datetime.date(2024, 1, 4)
    )
    assert rate == 75.0


def test_completion_rate_empty():
    assert _make_habit([]).completion_rate() == 0.0