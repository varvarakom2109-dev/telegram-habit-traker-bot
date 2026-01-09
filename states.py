from aiogram.fsm.state import State, StatesGroup

class AddHabit(StatesGroup):
    waiting_for_title = State()
    waiting_for_time = State()
    
class EditHabit(StatesGroup):
    waiting_for_new_title = State()
    waiting_for_new_time = State()