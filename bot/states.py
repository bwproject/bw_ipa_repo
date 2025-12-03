from aiogram.fsm.state import State, StatesGroup

class MetaStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_bundle = State()
    waiting_for_version = State()
    waiting_for_icon = State()