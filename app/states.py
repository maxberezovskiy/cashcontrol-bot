from aiogram.fsm.state import State, StatesGroup


class AddTransaction(StatesGroup):
    choosing_type = State()
    entering_amount = State()
    choosing_account = State()
    choosing_category = State()
    entering_note = State()
