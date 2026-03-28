from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    choose_role = State()
    enter_name = State()
    enter_phone = State()
    enter_grade = State()
    enter_child_name = State()
    confirm = State()

class TrialLesson(StatesGroup):
    choose_course = State()
    enter_name = State()
    enter_phone = State()
    enter_date = State()
    enter_time = State()
    confirm = State()

class Payment(StatesGroup):
    choose_course = State()
    choose_month = State()
    upload_receipt = State()
    confirm = State()

class SubmitHomework(StatesGroup):
    choose_homework = State()
    choose_type = State()
    enter_content = State()
    confirm = State()

class CreateHomework(StatesGroup):
    choose_course = State()
    enter_title = State()
    enter_description = State()
    enter_deadline = State()
    attach_file = State()
    confirm = State()

class CreateNews(StatesGroup):
    enter_title = State()
    enter_body = State()
    attach_image = State()
    choose_category = State()
    preview = State()

class Broadcast(StatesGroup):
    enter_text = State()
    attach_image = State()
    choose_target = State()
    confirm = State()

class AIDialog(StatesGroup):
    in_dialog = State()

class AdminCreateLesson(StatesGroup):
    choose_course = State()
    enter_date = State()
    enter_time = State()
    enter_room = State()
    confirm = State()
