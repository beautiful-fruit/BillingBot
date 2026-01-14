from discord import Bot, Interaction

from datetime import datetime
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
from os import getenv

from db import get_db
from repository.borrow_repository import BorrowRepository
from repository.return_repository import ReturnRepository
from utils.edit_origin_message import request_accept, request_reject, request_timeout

CUSTOM_ID_PREFIX = getenv("CUSTOM_ID_PREFIX", "default_prefix")


async def checker(bot: Bot, interaction: Interaction) -> bool:
    custom_id = interaction.custom_id
    return custom_id is not None and custom_id.startswith(CUSTOM_ID_PREFIX)


async def func(bot: Bot, interaction: Interaction):
    custom_id = interaction.custom_id
    if custom_id is None:
        return

    custom_id = custom_id.removeprefix(CUSTOM_ID_PREFIX)

    is_confirm = custom_id.startswith("confirm")
    custom_id = custom_id.removeprefix("confirm_" if is_confirm else "reject_")

    is_borrow = custom_id.startswith("borrow")
    custom_id = custom_id.removeprefix("borrow_" if is_borrow else "return_")

    custom_id = custom_id.removeprefix("trgs_")
    target_user_id = int(custom_id.split("_trge")[0])
    custom_id = custom_id.removeprefix(f"{target_user_id}_trge_")

    uid = int(custom_id.removeprefix("uid_"))

    original_message = interaction.message
    if original_message is None:
        await interaction.respond("找不到原始訊息，無法處理此操作。", ephemeral=True)
        return

    user = interaction.user
    if user is None or len(original_message.mentions) != 2:
        await interaction.respond("無法辨識操作的使用者。", ephemeral=True)
        return
    
    if user.id != target_user_id:
        await interaction.respond("你無權限操作此按鈕。", ephemeral=True)
        return

    delta_time = datetime.now(UTC) - original_message.created_at
    if delta_time.total_seconds() > 300:
        await interaction.respond("此按鈕已過期，無法操作。", ephemeral=True)
        await request_timeout(
            message=original_message,
            uid=uid,
            is_borrow=is_borrow
        )

        return
    
    if is_confirm:
        await interaction.respond("操作已確認。", ephemeral=True)
        await request_accept(
            message=original_message,
            uid=uid,
            is_borrow=is_borrow
        )
    else:
        await interaction.respond("操作已拒絕。", ephemeral=True)
        await request_reject(
            message=original_message,
            uid=uid,
            is_borrow=is_borrow
        )
