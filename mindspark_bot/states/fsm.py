from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    role = State()
    name = State()
    phone = State()


class PaymentFlow(StatesGroup):
    receipt = State()


class AdminCourse(StatesGroup):
    title = State()
    description = State()
    price = State()
    subscription = State()
    format = State()


class AdminLesson(StatesGroup):
    course = State()
    starts_at = State()
    capacity = State()


class AnnouncementFlow(StatesGroup):
    text = State()
