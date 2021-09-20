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
Hello there, I am *Shizuka Minamoto* - I'm here to help you to manage your chats with ease. 

➡️ Just add me in your group as admin .

Hit /help to know my commands .

You can get my news everyday at @zbotscreator .

Use the /privacy command to view the privacy policy, and interact with your data.
"""
G_START_TEXT = """
Hello Shizuka Minamoto here , How can I help you ?
"""
GREYSON_HOME_TEXT = """
*Excellent!* \nNow the Bot is ready to use!\n\nUse /help to Know all modules and features
`All commands can be used with / ? or !`
"""
SOURCEG_STRING = """Oh you want my channel link . I am built in python 3 , Using the python-telegram-bot library, and am fully open source .
\nDon't forgot to join in my channel 🍴 and star 🌟 the link . \n\nCheck my channel below 👇 \n⚙️ Update ⚙️ - [Click here](https://t.me/Zbotscreator)"""

buttons = [
    [
        InlineKeyboardButton(
            text="➕️ Add Shizuka Minamoto to chat!  ➕️", url="t.me/MrGreysonBot?startgroup=true"),
    ],
    [
        InlineKeyboardButton(text="📚 Guide 📚", callback_data="guidemenu_"),
        InlineKeyboardButton(text="⚒️ Support 🛠", callback_data="support_"),
    ],
    [
        InlineKeyboardButton(
            text="🎥 Configuration Tutorial 🎥", callback_data="tutmanu_"
        ),
    ],
]

gbuttons = [[InlineKeyboardButton(text="⚙️ help ⚙️",
                                  url="http://t.me/MrGreysonBot?start=help")]]

videobuttons = [[InlineKeyboardButton(text="✅ Done ✅",
                                  callback_data="tutmanu_home")]]

HELP_STRINGS = """
*Help*
Hey! My name is Shizuka Minamoto . I am a group management bot, here to help you get around and keep the order in your groups!

I have lots of handy features, such as flood control, a warning system, a note keeping system, and even predetermined replies on certain keywords.

*Helpful commands* :
✪ /start: Starts me! You've probably already used this. 
✪ /help: Sends this message; I'll tell you more about myself!
✪ /source: Gives you my source .

If you have any bugs or questions on how to use me head to @GreysonChats. \n\nAll commands can be used with the following: / !\n\nAnd the following :-"""

GreysonG_IMG = "https://telegra.ph/file/83dbae46536c4f88a28b7.jpg"

Greysontut_VID = "https://telegra.ph/file/f0df0d42c1d2a189d8c61.mp4"

SOURCE_STRING = """Oh you want my source . I am built in python 3 , Using the python-telegram-bot library, and am fully open source .
\nDon't forgot to fork 🍴 and star 🌟 the repo . \n\nCheck my source below 👇"""

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
    imported_module = importlib.import_module("GreysonBot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if imported_module.__mod_name__.lower() not in IMPORTED:
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
    dispatcher.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=keyboard,
    )


@run_async
def test(update: Update, context: CallbackContext):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text("This person edited a message")
    print(update.effective_message)


@run_async
def start(update: Update, context: CallbackContext):
    args = context.args
    uptime = get_readable_time((time.time() - StartTime))
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower().startswith("ghelp_"):
                mod = args[0].lower().split("_", 1)[1]
                if not HELPABLE.get(mod, False):
                    return
                send_help(
                    update.effective_chat.id,
                    HELPABLE[mod].__help__,
                    InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="⬅️ Back", callback_data="help_back")]]
                    ),
                )

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
        update.effective_message.reply_photo(
            GreysonG_IMG,
            G_START_TEXT,
            reply_markup=InlineKeyboardMarkup(gbuttons),
            parse_mode=ParseMode.MARKDOWN,
            timeout=60,
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
    keyboard = [[InlineKeyboardButton(text="➕ Add me ➕",url="t.me/MrGreysonBot?startgroup=true"),InlineKeyboardButton(text="⚙️ Help ⚙️",callback_data="help_back")]]
    keyboard += [[InlineKeyboardButton(text="📖 Guide 📖", callback_data="guidemenu_"),InlineKeyboardButton(text="📱Tutorial📱",callback_data="tutmanu_")]]

    update.effective_message.reply_text(
        PM_START_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
        timeout=60,
        disable_web_page_preview=False,
    )

def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    LOGGER.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    message = (
        "An exception was raised while handling an update\n"
        "<pre>update = {}</pre>\n\n"
        "<pre>{}</pre>"
    ).format(
        html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False)),
        html.escape(tb),
    )

    if len(message) >= 4096:
        message = message[:4096]
    # Finally, send the message
    context.bot.send_message(chat_id=OWNER_ID, text=message, parse_mode=ParseMode.HTML)


# for test purposes
def error_callback(update: Update, context: CallbackContext):
    error = context.error
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
def help_button(update, context):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)

    print(query.message.chat.id)

    try:
        if mod_match:
            module = mod_match.group(1)
            text = (
                "Here is the help for the *{}* module:\n".format(
                    HELPABLE[module].__mod_name__
                )
                + HELPABLE[module].__help__
            )
            query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="Back",callback_data="help_back"),InlineKeyboardButton(text="Home",callback_data="bot_start")]]
                ),
            )

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                ),
            )

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, HELPABLE, "help")
                ),
            )

        elif back_match:
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, HELPABLE, "help")
                ),
            )

        # ensure no spinny white circle
        context.bot.answer_callback_query(query.id)
        # query.message.delete()

    except BadRequest:
        pass


@run_async
def greyson_about_callback(update, context):
    query = update.callback_query
    if query.data == "greyson_":
        query.message.edit_text(
            text=""" My name is *Greyson* , I have been written in python3 using mixed libraries. I'm online since 14 June 2021 and is constantly updated! \n
*Bot Version*: _3.1_ \n
*Bot Admins* : 
• @kunaldiwan - bot creator and main developer 
• @Grizzypal - server manager and developer
• @Jimmioooo - support director \n
*And finally special thanks of gratitude to all my users who relied on me for managing their groups, I hope you will always like me; My developers are constantly working to improve me!*""",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(                   
                          [[
                              InlineKeyboardButton(
                              text="Updates Channel",
                              url="http://t.me/GraysonNews"),
                              InlineKeyboardButton(
                              text="Support Chat",
                              url="http://t.me/GreysonChats")
                          ],
                          [
                              InlineKeyboardButton(
                              text="Source",
                              url="https://github.com/Kunal-Diwan/GreysonBot"),
                              InlineKeyboardButton(
                              text="Go Back",
                              callback_data="guidemenu_")                  
                          ]])) 
@run_async
def Greyson_tut_callback(update, context):
    query = update.callback_query
    if query.data == "tutmanu_":
        query.message.edit_text(
            text=f"*Welcome to the Greyson configuration tutorial.* "
            f"\n\n👇 The first thing to do is to *add Greyson to your group*! For doing that, press the under button and select your group, then press *Done* to continue the tutorial. 👇",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="➕️ Add Grayson to chat!  ➕️", url="t.me/MrGreysonBot?startgroup=true"
                        )
                    ],
                    [InlineKeyboardButton(text="✅ Done ✅", callback_data="tutmanu_howto")],
                ]
            ),
        )
    elif query.data == "tutmanu_howto":
        query.message.edit_text(
            text=f"* Ok, well done! *"
            f"\nNow for let me work correctly, you need to make me *Admin of your Group*! \n"
            f"\nTo do that, follow this easy steps:\n"
            f"▫️ Go to your group \n▫️ Press the Group's name \n▫️ Press Modify \n▫️ Press on Administrator \n▫️ Press Add Administrator \n▫️ Press the Magnifying Glass \n▫️ Search @MrGreysonBot \n▫️ Confirm"
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
                    [InlineKeyboardButton(text="✅ Done ✅", callback_data="tutmanu_home")],
                ]
            ),
        )
    elif query.data == "tutmanu_home":
        update.effective_message.reply_text(
            GREYSON_HOME_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="🏡 Home 🏡", callback_data="bot_start")]]
            ),
        )

    elif query.data == "tutmanu_video":
        update.effective_message.reply_animation(
            Greysontut_VID,
            reply_markup=InlineKeyboardMarkup(videobuttons),
            parse_mode=ParseMode.MARKDOWN,
            timeout=60,
        )


@run_async
def Support_about_callback(update, context):
    query = update.callback_query
    if query.data == "support_":
        query.message.edit_text(
            text=""" Hi 👋 I'm *Greyson*
                 \nCheck my support below 👇\n\nNews channel 📣 - @GraysonNews \nSupport Chat 💬 - @GreysonChats. \n\n*Then also your query has not solved you can contact Main developer 👨‍💻* - @kunaldiwan . """,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="⬅️ Menu", callback_data="support_back")
                 ]
                ]
            ),
        )
    elif query.data == "support_back":
        query.message.edit_text(
                PM_START_TEXT,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
                disable_web_page_preview=False,
        )

@run_async
def Greyson_guide_callback(update, context):
    query = update.callback_query
    if query.data == "guidemenu_":
        query.message.edit_text(
            text=f"Hi again! I'am a full-fledged group management bot built to help you manage your group easily ."
                 f"\n\nI can do lot of stuff, some of them are: \n • Restrict users who flood your chat using my *anti-flood* module."
                 f"\n • Safeguard your group with the advanced and handy *Antispam system* ."
                 f"\n • Greet users with media + text and buttons, with proper formatting. \n • Save notes and filters with proper formatting and reply markup ."
                 f"\n\n*Note:*I need to be promoted with proper admin permissions to fuction properly. \n\nCheck *Setup Guide* to learn on setting up the bot and on *help* to learn more.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                  [
                    InlineKeyboardButton(text="Setup Guide", callback_data="guidemenu_setguide"),
                    InlineKeyboardButton(text="T & C", callback_data="guidemenu_tac")
                  ],
                 [
                    InlineKeyboardButton(text="About 🤖", callback_data="greyson_"),
                    InlineKeyboardButton(text="❔ Help", callback_data="help_back")
                  ],
                 [
                    InlineKeyboardButton(text="🔙 Back", callback_data="guidemenu_back")
                 ] 
                ]
            ),
        )
    elif query.data == "guidemenu_back":
        query.message.edit_text(
                PM_START_TEXT,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60, 
            )
        
    elif query.data == "guidemenu_setguide":
        query.message.edit_text(
            text=f"* ｢ Setup Guide 」\n*"
                 f"\nYou can add me to your group by clicking this [link](http://t.me/MrGreysonBot?startgroup=true) and selecting the chat. \nRead *Admin Permissions* and *Anti-spam* for basic info."
                 f"\n\nRead Detailed Setup Guide to learn about setting up the bot in detail. (Recommended) .\nIf you need help with further instructions feel free to ask in @GreysonChats."
                 f"",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(text="Admins Settings", callback_data="guidemenu_permis"),
                InlineKeyboardButton(text="Anti Spam", callback_data="guidemenu_spamprot")],
                [
                InlineKeyboardButton(text="🔙 Back", callback_data="guidemenu_")]
                                               ]),
        )
    elif query.data == "guidemenu_credit":
        query.message.edit_text(
            text=f"*{dispatcher.bot.first_name} is a powerful bot for managing groups with additional features.*"
                 f"\n\nThanks to Paul for his [Marie Bot](http://github.com/PaulSonOfLars/tgbot) . \n\nBase of [Saitama](https://github.com/AnimeKaizoku/SaitamaRobot)."
                 f"\n\n{dispatcher.bot.first_name}'s Licensed Under The GNU _(General Public License v3.0)_"
                 f"\n\nIf any question about {dispatcher.bot.first_name}, \nLet us know at Support Chat.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="☎️ Support",url="t.me/GreysonChats"),InlineKeyboardButton(text="🔙 Back",callback_data="guidemenu_tac")]]),
        )
    elif query.data == "guidemenu_permis":
        query.message.edit_text(
            text=f"<b> ｢ Admin Permissions 」</b>"
                 f"\nTo avoid slowing down, {dispatcher.bot.first_name} caches admin rights for each user. This cache lasts about 10 minutes; this may change in the future. This means that if you promote a user manually (without using the /promote command), {dispatcher.bot.first_name} will only find out ~10 minutes later."
                 f"\n\nIF you want to update them immediately, you can use the /admincache command,thta'll force {dispatcher.bot.first_name} to check who the admins are again and their permissions"
                 f"\n\nIf you are getting a message saying:"
                 f"\n<Code>You must be this chat administrator to perform this action!</code>"
                 f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
                 f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="❔ Help",callback_data="help_back"),InlineKeyboardButton(text="🔙 Back",callback_data="guidemenu_setguide")]]),
        )
    elif query.data == "guidemenu_spamprot":
        query.message.edit_text(
            text="* ｢ Anti-Spam Settings 」*"
                 "\n\n*Antispam :*"
                 "\nBy enabling this, you can protect your groups free from scammers/spammers."
                 "\nRun /antispam on in your chat to enable"
                 "\nAppeal Chat: @GreysonChats"
                 "\n\n • *Anti-Flood* allows you to keep your chat clean from flooding."
                 "\n • With the help of *Blacklists* you can blacklist words,sentences and stickers which you don't want to be used by group members."
                 "\n • By enabling *Reports*, admins get notified when users reports in chat."
                 "\n • *Locks* allows you to lock/restrict some comman items in telegram world."
                 "\n • *Warnings* allows to warn users and set auto-warns ."
                 "\n • *Welcome Mute* helps you prevent spambots or users flooding/spamming your group. Check *Greetings* for more info.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="❔ Help",callback_data="help_back"),InlineKeyboardButton(text="🔙 Back",callback_data="guidemenu_setguide")]]),
        )
    elif query.data == "guidemenu_tac":
        query.message.edit_text(
            text=f"<b> ｢ Terms and Conditions 」</b>\n"
                 f"\n<i>To use this bot, You need to agree with Terms and Conditions.</i>\n"
                 f"\n✪ Only your first name, last name (if any) and username (if any) is stored for a convenient communication!"
                 f"\n✪ No group ID or it's messages are stored, we respect everyone's privacy."
                 f"\n✪ Messages between Bot and you is only infront of your eyes and there is no because of it."
                 f"\n✪ If you need to ask anything about this bot, Go @{SUPPORT_CHAT}."
                 f"\n✪ If you asking nonsense in Support Chat, you will get warned/banned."
                 f"\n✪ Watch your group, if someone is spamming your group, you can use the report feature of your Telegram Client."
                 f"\n✪ Sharing NSFW in Support Chat, will reward you GBAN nd reported to Telegram as well."
                 f"\n\nFor any kind of help, related to this bot, Join @{SUPPORT_CHAT}."
                 f"\n\n<i>Terms & Conditions might changed anytime</i>\n",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [
                  [
                    InlineKeyboardButton(text="Credits", callback_data="guidemenu_credit"),
                    InlineKeyboardButton(text="🔙 Back", callback_data="guidemenu_")
                  ]])
        )

@run_async
def get_help(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:
        if len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
            module = args[1].lower()
            update.effective_message.reply_text(
                f"Contact me in PM to get help of {module.capitalize()}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Help",
                                url="t.me/{}?start=ghelp_{}".format(
                                    context.bot.username, module
                                ),
                            )
                        ]
                    ]
                ),
            )
            return
        update.effective_message.reply_text(
            "Contact me in PM to get the list of possible commands.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Help",
                            url="t.me/{}?start=help".format(context.bot.username),
                        )
                    ]
                ]
            ),
        )
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = (
            "Here is the available help for the *{}* module:\n".format(
                HELPABLE[module].__mod_name__
            )
            + HELPABLE[module].__help__
        )
        send_help(
            chat.id,
            text,
            InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="🔙 Back", callback_data="help_back")]]
            ),
        )

    else:
        send_help(chat.id, HELP_STRINGS)


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id))
                for mod in USER_SETTINGS.values()
            )
            dispatcher.bot.send_message(
                user_id,
                "These are your current settings:" + "\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            dispatcher.bot.send_message(
                user_id,
                "Seems like there aren't any user specific settings available :'(",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(
                user_id,
                text="Which module would you like to check {}'s settings for?".format(
                    chat_name
                ),
                reply_markup=Inline.KeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
        else:
            dispatcher.bot.send_message(
                user_id,
                "Seems like there aren't any chat settings available :'(\nSend this "
                "in a group chat you're admin in to find its current settings!",
                parse_mode=ParseMode.MARKDOWN,
            )


@run_async
def settings_button(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    bot = context.bot
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(
                escape_markdown(chat.title), CHAT_SETTINGS[module].__mod_name__
            ) + CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Back",
                                callback_data="stngs_back({})".format(chat_id),
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                text="Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(escape_markdown(chat.title)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message not in [
            "Message is not modified",
            "Query_id_invalid",
            "Message can't be deleted",
        ]:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


@run_async
def get_settings(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "Click here to get this chat's settings, as well as yours."
            msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Settings",
                                url="t.me/{}?start=stngs_{}".format(
                                    context.bot.username, chat.id
                                ),
                            )
                        ]
                    ]
                ),
            )
        else:
            text = "Click here to check your settings."

    else:
        send_settings(chat.id, user.id, True)

@run_async
def source(update: Update, context: CallbackContext):
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]
    bot = context.bot
    if chat.type == "private":
        update.effective_message.reply_text(
            SOURCE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(
                [
                  [
                    InlineKeyboardButton(text="↗️ Source ↗️", url="https://github.com/Kunal-Diwan/GreysonBot")
                 ] 
                ]
            ),
        )

        if OWNER_ID != 1701601729 and MAINTAINER_LINK:
            update.effective_message.reply_text(
                "I am maintained by "
                "[him]({})".format(MAINTAINER_LINK),
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        try:
            bot.send_message(
                user.id,
                SOURCEG_STRING,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )

            update.effective_message.reply_text(
                "I have PM you about my source!"
            )
        except Unauthorized:
            update.effective_message.reply_text(
                "Contact me in PM first to get source information."
            )

def migrate_chats(update: Update, context: CallbackContext):
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

    if SUPPORT_CHAT is not None and isinstance(SUPPORT_CHAT, str):
        try:
            dispatcher.bot.sendMessage(f"@{SUPPORT_CHAT}", "Yes I'm online")
        except Unauthorized:
            LOGGER.warning(
                "Bot isnt able to send message to support_chat, go and check!"
            )
        except BadRequest as e:
            LOGGER.warning(e.message)

    test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start)

    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_.*")
    start_callback_handler = CallbackQueryHandler(
        send_start, pattern=r"bot_start")
    dispatcher.add_handler(start_callback_handler)

    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")

    about_callback_handler = CallbackQueryHandler(greyson_about_callback, pattern=r"greyson_")
    source_callback_handler = CallbackQueryHandler(Support_about_callback, pattern=r"support_")
    guide_callback_handler = CallbackQueryHandler(
        Greyson_guide_callback, pattern=r"guidemenu_"
    )
    tut_callback_handler = CallbackQueryHandler(
        Greyson_tut_callback, pattern=r"tutmanu_"
    )
  
    source_handler = CommandHandler("source", source)
    migrate_handler = MessageHandler(Filters.status_update.migrate, migrate_chats)

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(guide_callback_handler)
    dispatcher.add_handler(tut_callback_handler)
    dispatcher.add_handler(about_callback_handler)
    dispatcher.add_handler(source_callback_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(source_handler)

    dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN, certificate=open(CERT_PATH, "rb"))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Greyson Running ......")
        updater.start_polling(timeout=15, read_latency=4, clean=True)
        updater.bot.send_message(
            chat_id=MESSAGE_DUMP,
            text="I have been deployed successfully ...... Ready to run 🏃 ")

    if len(argv) not in (1, 3, 4):
        telethn.disconnect()
    else:
        telethn.run_until_disconnected()

    updater.idle()


if __name__ == "__main__":
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    telethn.start(bot_token=TOKEN)
    pbot.start()
    main()
