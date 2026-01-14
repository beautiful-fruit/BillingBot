from discord import ApplicationContext, Member, option

from bot import bot


@bot.slash_command(name="return", description="Record a return transaction")
@option("return_to", description="The member to whom the return is made", type=Member, required=True)
@option("amount", description="The amount being returned", type=int, required=True, min_value=1)
async def return_to(
    ctx: ApplicationContext,
    return_to: Member,
    amount: int
):
    pass
