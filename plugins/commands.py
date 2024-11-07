from info import *
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


@Client.on_message(filters.command("start"))
async def start(client, message):
    buttons = [[
        InlineKeyboardButton('👨‍💻 𝖣𝖾𝗏𝖾𝗅𝗈𝗉𝖾𝗋', url=f"https://telegram.me/HarixTGx")
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    text=f"""<b>👋 𝖧𝖾𝗅𝗅𝗈 {message.from_user.mention}!

𝖨'𝗆 𝖺 𝖲𝗂𝗇𝗀𝗅𝖾 𝖯𝖺𝗀𝖾 𝖬𝖾𝗌𝗌𝖺𝗀𝖾 𝖢𝗈𝗆𝗉𝗂𝗅𝖾𝗋 𝖡𝗈𝗍 📝

💡 𝖥𝖾𝖺𝗍𝗎𝗋𝖾𝗌:

- 𝖢𝗈𝗆𝗉𝗂𝗅𝖾 𝖺𝗅𝗅 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌 𝗂𝗇 𝗈𝗇𝖾 𝗉𝖺𝗀𝖾
- 𝖠𝗎𝗍𝗈-𝗎𝗉𝖽𝖺𝗍𝖾 𝖼𝗈𝗆𝗉𝗂𝗅𝖾𝖽 𝗅𝗂𝗌𝗍
- 𝖠𝖽𝗆𝗂𝗇-𝗈𝗇𝗅𝗒 𝖿𝗎𝗇𝖼𝗍𝗂𝗈𝗇𝖺𝗅𝗂𝗍𝗒
- 𝖬𝖾𝗌𝗌𝖺𝗀𝖾 𝖺𝖼𝗍𝗂𝗏𝗂𝗍𝗒 𝗍𝗋𝖺𝖼𝗄𝗂𝗇𝗀</b>"""
    await message.reply_text(
        text=text,
        reply_markup=reply_markup,
        quote=True,
        parse_mode=enums.ParseMode.HTML
    )

names = []
message_id = None

@Client.on_message(filters.group & filters.text & ~filters.command(['done', 'start']))
async def handle_message(client, message):
    global names, message_id
    names.append(message.text.strip())
    compiled_message = "\n".join([f"<b>{i + 1}. {name}</b>" for i, name in enumerate(names)])
    if message_id is None:
        sent_message = await message.reply_text(compiled_message)
        message_id = sent_message.id
    else:
        await client.edit_message_text(chat_id=message.chat.id, message_id=message_id, text=compiled_message)

@Client.on_message(filters.group & filters.user(ADMINS) & filters.command("done"))
async def start(client, message):
    global names, message_id
    names = []
    message_id = None 
    await message.reply_text("<b>Single Page All Message Done ✅</b>")
