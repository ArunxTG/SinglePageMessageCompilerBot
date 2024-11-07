from info import *
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Dictionary to store message IDs and names for each group
group_data = {}

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

@Client.on_message(filters.chat_type.supergroup & filters.chat_admin_rights & filters.text & ~filters.command(['done', 'start', 'connect', 'disconnect']))
async def handle_message(client, message):
    global group_data
    chat_id = message.chat.id

    if chat_id not in group_data:
        group_data[chat_id] = (None, [])

    message_id, names = group_data[chat_id]
    names.append(message.text.strip())
    compiled_message = "\n".join([f"{i + 1}. {name}" for i, name in enumerate(names)])

    if message_id is None:
        sent_message = await message.reply_text(compiled_message)
        group_data[chat_id] = (sent_message.id, names)
    else:
        await client.edit_message_text(chat_id=message.chat.id, message_id=message_id, text=compiled_message)
        group_data[chat_id] = (message_id, names)

@Client.on_message(filters.chat_type.supergroup & filters.chat_admin_rights & filters.command("done"))
async def done(client, message):
    global group_data
    chat_id = message.chat.id

    if chat_id in group_data:
        message_id, names = group_data.pop(chat_id)
        await client.delete_messages(chat_id=message.chat.id, message_ids=[message_id])
        await message.reply_text("<b>Single Page All Message Done ✅<b>")

@Client.on_message(filters.user(ADMINS) & filters.command("connect"))
async def connect_to_group(client, message):
    # Connect the bot to the group
    await client.join_chat(message.chat.id)
    await message.reply_text("<b>Bot connected to the group.</b>")

@Client.on_message(filters.user(ADMINS) & filters.command("disconnect"))
async def disconnect_from_group(client, message):
    # Disconnect the bot from the group
    await client.leave_chat(message.chat.id)
    await message.reply_text("<b>Bot disconnected from the group.</b>")
