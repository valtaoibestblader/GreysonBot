import importlib
import time
import re
from sys import argv
from typing import Optional

from GreysonBot import (
    ALLOW_EXCL,
    CERT_PATH,
    MAINTAINER_LINK,
    LOGGER,
    OWNER_ID,
    PORT,
    SUPPORT_CHAT,
    TOKEN,
    MESSAGE_DUMP,
    URL,
    WEBHOOK,
    SUPPORT_CHAT,
    dispatcher,
    StartTime,
    telethn,
    pbot,
    updater,
)

# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from GreysonBot.modules import ALL_MODULES
from GreysonBot.modules.helper_funcs.chat_status import is_user_admin
from GreysonBot.modules.helper_funcs.misc import paginate_modules
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import (
    BadRequest,
    ChatMigrated,
    NetworkError,
    TelegramError,
    TimedOut,
    Unauthorized,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.ext.dispatcher import DispatcherHandlerStop, run_async
from telegram.utils.helpers import escape_markdown


def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time


PM_START_TEXT = """
hello there , I am Filterry - Telegram group filter bot . 

It can help you to add any type of filter in group with more speciality and functions .

Hit /help to know more .....

I am maintained by [this person](tg://user?id={}) .

"""
GREYSON_SETUP_TEXT = """
*All setup done!* \nNow the Bot is ready to use!\n\nUse /help to Know all modules and features \n
`All commands can be used with / ? or !`
"""

buttons = [
    [
        InlineKeyboardButton(
            text="➕️ Add Filterry to chat!  ➕️", url="t.me/FilterryBot?startgroup=true"),
    ],
    [
        InlineKeyboardButton(text="ℹ️ About", callback_data="Filterry_"),
        InlineKeyboardButton(text="⚙️ Help ⚙️", callback_data="help_back"),
    ],
    [
        InlineKeyboardButton(
            text="🎥 Configuration Tutorial 🎥", callback_data="tutmanu_"
        ),
    ],
]

HELP_STRINGS = """

Hello! my name *{}*. I am advance group filter bot .

*Usual commands* :- 

• /start - Start me again 
• /connect - Connect group
• /source - Check about my source

""".format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "Powered by @DevelopedBots")

SOURCE_STRING = """Oh you want my source .... 

💾 Source 💾 - [Click here](https://github.com/Kunal-Diwan/Filterry-Bot) ."""

Filterrytut_VID = "https://telegra.ph/file/f0df0d42c1d2a189d8c61.mp4"

Filterrytut_SVID = "https://telegra.ph/file/b8260e300bdc998e9c3db.mp4"

videobuttons = [[InlineKeyboardButton(text="✅ Done ✅",
                                  callback_data="tutmanu_setup")]]

setupbuttons = [[InlineKeyboardButton(text="🏡 Home 🏡",
                                  callback_data="tutmanu_home")]]

homebuttons = [[InlineKeyboardButton(text="🏡 Home 🏡",
                                  callback_data="bot_start")]]

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("GeeysonBot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if not imported_module.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard)


@run_async
def test(bot: Bot, update: Update):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text("This person edited a message")
    print(update.effective_message)


@run_async
def start(bot: Bot, update: Update, args: List[str]):
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            update.effective_message.reply_text(
                PM_START_TEXT,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
            )
    else:
        update.effective_message.reply_text("Filterry here 👋. Check help if you don't know how to use me !"),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="⚙️ Help ⚙️", url="t.me/FilterryBot?start=help")]]
            ),
        )

def send_start(update, context):
    # Try to remove old message
    try:
        query = update.callback_query
        query.message.delete()
    except BaseException:
        pass

    chat = update.effective_chat  # type: Optional[Chat]
    first_name = update.effective_user.first_name
    text = PM_START_TEXT
    keyboard = [[InlineKeyboardButton(text="➕ Add me ➕",url="t.me/FilterryBot?startgroup=true"),InlineKeyboardButton(text="⚙️ Help ⚙️",callback_data="help_back")]]
    keyboard += [[InlineKeyboardButton(text="🌐 Connect 🌐", callback_data="main_connect"),InlineKeyboardButton(text="📱Tutorial📱",callback_data="tutmanu_")]]

    update.effective_message.reply_text(
        PM_START_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
        timeout=60,
        disable_web_page_preview=False,
    )


# for test purposes
def error_callback(bot, update, error):
    try:
        raise error
    except Unauthorized:
        print("no nono1")
        print(error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        print("no nono2")
        print("BadRequest caught")
        print(error)

        # handle malformed requests - read more below!
    except TimedOut:
        print("no nono3")
        # handle slow connection problems
    except NetworkError:
        print("no nono4")
        # handle other connection problems
    except ChatMigrated as err:
        print("no nono5")
        print(err)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(error)
        # handle all other telegram related errors


@run_async
def help_button(bot: Bot, update: Update):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            text = "Here is the help for the *{}* module:\n".format(HELPABLE[module].__mod_name__) \
                   + HELPABLE[module].__help__
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="⬅️ Back", callback_data="help_back")]]))

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, HELPABLE, "help")))

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, HELPABLE, "help")))

        elif back_match:
            query.message.reply_text(text=HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")))

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in help buttons. %s", str(query.data))


@run_async
def get_help(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:

        update.effective_message.reply_text("Contact me in PM to get the list of possible commands.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="Help",
                                                                       url="t.me/{}?start=help".format(
                                                                           bot.username))]]))
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = "Here is the available help for the *{}* module:\n".format(HELPABLE[module].__mod_name__) \
               + HELPABLE[module].__help__
        send_help(chat.id, text, InlineKeyboardMarkup([[InlineKeyboardButton(text="Back", callback_data="help_back")]]))

    else:
        send_help(chat.id, HELP_STRINGS)


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id)) for mod in USER_SETTINGS.values())
            dispatcher.bot.send_message(user_id, "These are your current settings:" + "\n\n" + settings,
                                        parse_mode=ParseMode.MARKDOWN)

        else:
            dispatcher.bot.send_message(user_id, "Seems like there aren't any user specific settings available :'(",
                                        parse_mode=ParseMode.MARKDOWN)

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(user_id,
                                        text="Which module would you like to check {}'s settings for?".format(
                                            chat_name),
                                        reply_markup=InlineKeyboardMarkup(
                                            paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)))
        else:
            dispatcher.bot.send_message(user_id, "Seems like there aren't any chat settings available :'(\nSend this "
                                                 "in a group chat you're admin in to find its current settings!",
                                        parse_mode=ParseMode.MARKDOWN)


@run_async
def settings_button(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(escape_markdown(chat.title),
                                                                                     CHAT_SETTINGS[module].__mod_name__) + \
                   CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="Back",
                                                                callback_data="stngs_back({})".format(chat_id))]]))

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("Hi there! There are quite a few settings for {} - go ahead and pick what "
                                     "you're interested in.".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("Hi there! There are quite a few settings for {} - go ahead and pick what "
                                     "you're interested in.".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(text="Hi there! There are quite a few settings for {} - go ahead and pick what "
                                          "you're interested in.".format(escape_markdown(chat.title)),
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, CHAT_SETTINGS, "stngs",
                                                                                        chat=chat_id)))

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


@run_async
def get_settings(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(None, 1)

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "Click here to get this chat's settings, as well as yours."
            msg.reply_text(text,
                           reply_markup=InlineKeyboardMarkup(
                               [[InlineKeyboardButton(text="Settings",
                                                      url="t.me/{}?start=stngs_{}".format(
                                                          bot.username, chat.id))]]))
        else:
            text = "Click here to check your settings."

    else:
        send_settings(chat.id, user.id, True)

@run_async
def filterry_about_callback(update, context):
    query = update.callback_query
    if query.data == "filterry_":
        query.message.edit_text(
            text=""" My name is *Filterry* , I have been written in python3 using mixed libraries. \n
Bot Version - 3.1 \n
➡️ *Bot Developer 👨‍💻 - @kunaldiwan* \n
➡️ 🔔 Channel 🔔 - @DevelopedBots
➡️ 🔊 Group 🔊 - @DevelopedBotz

➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖""",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="Back 🔙", callback_data="filterry_back")
                 ]
                ]
            ),
        )
    elif query.data == "filterry_back":
        query.message.edit_text(
                PM_START_TEXT,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
                disable_web_page_preview=False,
        )


@run_async
def filterry_tut_callback(update, context):
    query = update.callback_query
    if query.data == "tutmanu_":
        query.message.edit_text(
            text=f"*Welcome to the Filterry configuration tutorial.* "
            f"\n\n👇 The first thing to do is to *add Filterry to your group*! For doing that, press the under button and select your group, then press *Continue* to continue the tutorial. 👇",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="➕️ Add Filterry to chat!  ➕️", url="t.me/FilterryBot?startgroup=true"
                        )
                    ],
                    [InlineKeyboardButton(text="✅ Continue ✅", callback_data="tutmanu_howto")],
                ]
            ),
        )
    elif query.data == "tutmanu_howto":
        query.message.edit_text(
            text=f"* Ok, well done! *"
            f"\nNow for let me work correctly, you need to make me *Admin of your Group*! \n"
            f"\nTo do that, follow this easy steps:\n"
            f"▫️ Go to your group \n▫️ Press the Group's name \n▫️ Press Modify \n▫️ Press on Administrator \n▫️ Press Add Administrator \n▫️ Press the Magnifying Glass \n▫️ Search @FilterryBot \n▫️ Confirm"
            f"",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="💾 Example Video 💾", callback_data="tutmanu_video"
                        ),
                    ],
                    [InlineKeyboardButton(text="✅ Done ✅", callback_data="tutmanu_setup")],
                ]
            ),
        )
    elif query.data == "tutmanu_setup":
        update.effective_message.reply_text("*Excellent* \n\nYou have added me to you are group admin now you can easily set filter in me \n\nClick on *Set up* to Know how to set filters ."),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="⚒️ Setup 🛠️", callback_data="tutmanu_setupvid")]]
            ),
        )

    elif query.data == "tutmanu_video":
        update.effective_message.reply_animation(
            Filterrytut_VID,
            reply_markup=InlineKeyboardMarkup(videobuttons),
            parse_mode=ParseMode.MARKDOWN,
            timeout=60,
          ),
       )

    elif query.data == "tutmanu_setupvid":
        update.effective_message.reply_animation(
            Filterrytut_SVID,
            reply_markup=InlineKeyboardMarkup(setupbuttons),
            parse_mode=ParseMode.MARKDOWN,
            timeout=60,
          ),
       )

    elif query.data == "tutmanu_home":
        update.effective_message.reply_text("*Now all setup done!* \nNow the Bot is ready to use!\n\nUse /help to Know all modules and features ."),
            reply_markup=InlineKeyboardMarkup(homebuttons),
            parse_mode=ParseMode.MARKDOWN,
            timeout=60,
        )


@run_async
def source(bot: Bot, update: Update):
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]

    if chat.type == "private":
        update.effective_message.reply_text(SOURCE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    else:
        try:
            bot.send_message(user.id, SOURCE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

            update.effective_message.reply_text("I've PM'ed you about my source!")
        except Unauthorized:
            update.effective_message.reply_text("Contact me in PM first to get source information.")


def migrate_chats(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    LOGGER.info("Successfully migrated!")
    raise DispatcherHandlerStop


def main():
    test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start, pass_args=True)

    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_")
    start_callback_handler = CallbackQueryHandler(
        send_start, pattern=r"bot_start")
    dispatcher.add_handler(start_callback_handler)

    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")
    
    about_callback_handler = CallbackQueryHandler(filterry_about_callback, pattern=r"filterry_")
    tut_callback_handler = CallbackQueryHandler(
        Filterry_tut_callback, pattern=r"tutmanu_"
    )

    source_handler = CommandHandler("source", source)
    migrate_handler = MessageHandler(Filters.status_update.migrate, migrate_chats)

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(tut_callback_handler)
    dispatcher.add_handler(about_callback_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(source_handler)

    # dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN,
                                    certificate=open(CERT_PATH, 'rb'))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Filterry running ....")
        updater.start_polling(timeout=15, read_latency=4)
        updater.bot.send_message(
            chat_id=MESSAGE_DUMP,
            text="I have been deployed successfully ...... Ready to run 🏃 ")

    updater.idle()


if __name__ == '__main__':
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    main()
