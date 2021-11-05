"""This module provides tools and code for
creating simple ToDo bot for Telegram"""

import logging
from functools import wraps
from typing import Any, Callable

from telegram import (Update,
                      InlineKeyboardButton,
                      InlineKeyboardMarkup,
                      Message,)

from telegram.ext import (Updater,
                          CommandHandler,
                          CallbackContext,
                          Filters,
                          CallbackQueryHandler,
                          MessageHandler,
                          PicklePersistence,
                          Job,
                          Dispatcher,)

from telegram.parsemode import ParseMode


class Memo():
    """Class representing separate memos

    :param text: Text data of memo
    :type text: str
    :param messages: List of messages, related to this memo
    :type messages: list[int]
    :param id: First message contained this memo,
        used like unique identificator
    :type id: str"""

    def __init__(self, message_id: int, text: str) -> None:
        """Constructor method

        :param message_id: Id of message representing memo
        :type message_id: int
        :param text: Text data of memo
        :type text: str"""
        self.id: str = str(message_id)
        self.messages: list[int] = [message_id]
        self.text: str = text
        super().__init__()

    def update(self, message_id: int) -> None:
        """Updates *messages* when memo listed once more

        :param message_id: Id of message that invoked memo
        :type message_id: int"""
        self.messages.append(message_id)


class MemoList():
    """Class representing memos associated with particular chat

    :param memos: List of memos in chat
    :type memos: list[Memo]"""

    def __init__(self) -> None:
        """Constructor method"""
        self.memos: list[Memo] = []
        super().__init__()

    def add_memo(self, message_id: int, text: str) -> str:
        """Adds new memo to :param:'memos'

        :param message_id: Id of message representing memo
        :type message_id: int
        :param text: Text data of memo
        :type text: str
        :return: Id of created :class:`Memo` object
        :rtype: str"""
        new_memo = Memo(message_id, text)
        self.memos.append(new_memo)
        return new_memo.id

    def remove(self, message_id: int) -> None:
        """Removes memo from list

        :param message_id: Id of message to be removed
        :type message_id: int
        :raises IndexError: No message with such index"""
        if len(self.memos) == 0:
            raise IndexError()
        for memo in self.memos:
            if message_id in memo.messages:
                self.memos.remove(memo)
                return None
        raise IndexError()

    def __getitem__(self, key: int) -> Memo:
        """Called to implement evaluation of self[key]

        :param key: Index of object to get
        :type key: int
        :return: Object with index *key*
        :rtype: Memo
        :raises IndexError: No memo with such index"""
        if key >= len(self.memos):
            raise IndexError()
        return self.memos[key]

    def __len__(self) -> int:
        """Called to implement the built-in function len()

        :returns: Length (the number of items) of :class:`MemoList`
        :rtype: int"""
        return len(self.memos)

    def get(self, message_id: int) -> Memo:
        """Get memo via message that contains it

        :param message_id: Message that contains memo
        :type message_id: int
        :raises IndexError: No memo associated with such message
        :returns: Memo associated with such message
        :rtype: Memo"""
        if len(self.memos) > 0:
            for memo in self.memos:
                if message_id in memo.messages:
                    return memo
            raise IndexError()
        raise IndexError()


logging.basicConfig(
    filename='example.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
    )

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    """Sends start message to user and initializes :class:`MemoList` for this chat

    :param update: Update data provided via API
    :type update: Update
    :param context: Context data provided via API
    :type context: CallbackContext"""
    context.chat_data["memos"] = MemoList()
    update.message.reply_text(
        "Чтобы добавить новую задачу, просто введите сообщение в этот чат.\n"
        "Чтобы отметить её как выполненную, нажмите по кнопке возле задачи.\n"
        "Чтобы добавить задачу с напоминанием через n минут, введите\n"
        "«/timed n задача для напоминания через 'n' минут»\n"
        "Список текущих задач можно просмотреть с помощью комманды /list"
        )


def init_check(context: CallbackContext) -> bool:
    """Check if *memos* present in chat data
    :param context: Context data provided via API
    :type context: CallbackContext"""
    if "memos" not in context.chat_data:
        context.chat_data["memos"] = MemoList()


def show_help(update: Update, context: CallbackContext) -> None:
    """Sends start message to user without inicialization of memos

    :param update: Update data provided via API
    :type update: Update
    :param context: Context data provided via API
    :type context: CallbackContext"""
    update.message.reply_text(
        "Чтобы добавить новую задачу, просто введите сообщение в этот чат.\n"
        "Чтобы отметить её как выполненную, нажмите по кнопке возле задачи.\n"
        "Чтобы добавить задачу с напоминанием через n минут, введите\n"
        "«/timed n задача для напоминания через 'n' минут»\n"
        "Список текущих задач можно просмотреть с помощью комманды /list"
        )


def inline(func: Callable):
    """Decorator for adding inline buttons

    :param func: Function to be decorated
    :type func: Callable
    :returns: Decorated function
    :rtype: Callable"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        check = InlineKeyboardButton("Отметить выполненным",
                                     callback_data="check")
        keyboard = InlineKeyboardMarkup([[check]])
        func(*args, **kwargs, keyboard=keyboard)
    return wrapper


@inline
def add(update: Update, context: CallbackContext,
        keyboard: InlineKeyboardMarkup = None) -> None:
    """Add memo to list and display it

    :param update: Update data provided via API
    :type update: Update
    :param context: Context data provided via API
    :type context: CallbackContext
    :param keyboard: Inline buttons layout
    :type keyboard: InlineKeyboardMarkup"""
    init_check(context)
    text: str = update.message.text
    message: Message = update.message.reply_text(text=text,
                                                 reply_markup=keyboard)
    context.chat_data["memos"].add_memo(message.message_id, message.text)


def complete(update: Update, context: CallbackContext) -> None:
    """Marks all mesages related to memo as completed and deletes
    memo from list

    :param update: Update data provided via API
    :type update: Update
    :param context: Context data provided via API
    :type context: CallbackContext"""
    chat_id = update.effective_message.chat_id
    message_id = update.effective_message.message_id
    text: str = "<s>" + update.effective_message.text + "</s>"
    memo: Memo = context.chat_data["memos"].get(message_id)
    messages = memo.messages
    for message in messages:
        context.bot.edit_message_text(text=text, parse_mode=ParseMode.HTML,
                                      chat_id=chat_id, message_id=message)
    context.chat_data["memos"].remove(message_id)
    remove_reminder(memo.id, context)


@inline
def list_memo(update: Update, context: CallbackContext,
              keyboard: InlineKeyboardMarkup) -> None:
    """List all active memos

    :param update: Update data provided via API
    :type update: Update
    :param context: Context data provided via API
    :type context: CallbackContext
    :param keyboard: Inline buttons layout
    :type keyboard: InlineKeyboardMarkup"""
    init_check(context)
    memos: MemoList = context.chat_data["memos"]
    if len(memos) > 0:
        for memo in memos:
            message = context.bot.send_message(
                chat_id=update.message.chat.id,
                text=memo.text,
                reply_markup=keyboard
                )
            memo.update(message.message_id)
    else:
        context.bot.send_message(chat_id=update.message.chat.id,
                                 text="Сейчас у вас нет активных задач")


@inline
def remind(context: CallbackContext,
           keyboard: InlineKeyboardMarkup = None) -> None:
    """Sends message with reminder

    :param context: Context data provided via API
    :type context: CallbackContext
    :param keyboard: Inline buttons layout
    :type keyboard: InlineKeyboardMarkup"""
    job: Job = context.job
    memo: Memo = job.context["memos"].get(job.context["message_id"])
    message = context.bot.send_message(chat_id=job.context["chat_id"],
                                       text=memo.text, reply_markup=keyboard)
    memo.update(message.message_id)


@inline
def timed(update: Update, context: CallbackContext,
          keyboard: InlineKeyboardMarkup) -> None:
    """Adds message with timed reminder and sends it

    :param update: Update data provided via API
    :type update: Update
    :param context: Context data provided via API
    :type context: CallbackContext
    :param keyboard: Inline buttons layout
    :type keyboard: InlineKeyboardMarkup"""
    init_check(context)
    args: list[str] = context.args
    if len(args) < 2:
        update.message.reply_text(text="Комманда введена неверно")
        return
    try:
        due: int = int(args.pop(0))*60
    except ValueError:
        update.message.reply_text(text="Комманда введена неверно")
        return
    if due <= 0:
        update.message.reply_text(text="Нельзя напомнить о чем-то в прошлом")
        return
    text: str = " ".join(args)
    pref = f"Напоминание сработет через {due/60} минут\n"
    message: Message = \
        update.message.reply_text(text=pref+text, reply_markup=keyboard)
    message_id: str = \
        context.chat_data["memos"].add_memo(message.message_id, text)
    job_context: dict[str, Any] = {
        "chat_id": update.message.chat.id,
        "text": text,
        "message_id": message.message_id,
        "memos": context.chat_data["memos"]
        }
    context.job_queue.run_once(remind, due, context=job_context,
                               name=message_id)


def remove_reminder(name: str, context: CallbackContext) -> bool:
    """Removes reminders from queue

    :param name: Name of job to remove
    :type name: str
    :param context: Context data provided via API
    :type context: CallbackContext
    :returns: Whether message was removed or not
    :rtype: bool"""
    current_jobs: tuple[Job] = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def unknown(update: Update, context: CallbackContext) -> None:
    """Unknown command handler
    :param update: Update data provided via API
    :type update: Update
    :param context: Context data provided via API
    :type context: CallbackContext"""
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Я не знаю эту команду")


if __name__ == "__main__":
    token: str = str()
    with open('.token', 'r', encoding="utf_8") as file:
        token = file.readline()

    updater = Updater(token=token, use_context=True,
                      persistence=PicklePersistence("data"))

    dispatcher: Dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("list", list_memo))
    dispatcher.add_handler(MessageHandler(~Filters.command, add))
    dispatcher.add_handler(CallbackQueryHandler(complete, pattern="check"))
    dispatcher.add_handler(CommandHandler("timed", timed))
    dispatcher.add_handler(CommandHandler("help", show_help))

    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    updater.start_polling()

    updater.idle()
