from time import time

from discord import Color, Embed, VoiceChannel
from discord.ext.commands import Bot, Cog, Context, has_permissions, hybrid_command

from utils import sform


class Moderation(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @hybrid_command(
        name="purge",
        help="Команда для удаления последних сообщений",
        usage="purge <кол-во>",
    )
    @has_permissions(manage_messages=True)
    async def purge_(self, ctx: Context, amt: int = 0):
        if amt == 0:
            return await ctx.send(f"Использование: {ctx.prefix}purge <кол-во>")

        channel = ctx.message.channel

        if ctx.interaction is None:
            return await channel.purge(limit=amt + 1)

        await ctx.interaction.response.defer(ephemeral=True, thinking=True)

        deleted = await channel.purge(limit=amt)

        return await ctx.interaction.followup.send(
            f"Удалено {len(deleted)} {sform(len(deleted), 'сообщение')}",
            ephemeral=True,
        )

    @hybrid_command(
        usage="move <название канала>",
        help="Команда для перемещения всех из одного канала в другой",
    )
    async def move(self, ctx, *, channel: str):
        if ctx.author.guild_permissions.move_members:
            if ctx.author.voice is None:
                return await ctx.send("Вы не подключены к голосовому каналу")
            if ctx.author.voice.channel.name.lower() == channel.lower():
                return await ctx.send("Уже подключен к голосовому каналу")
            channels = await ctx.guild.fetch_channels()
            for ch in channels:
                if isinstance(ch, VoiceChannel) and (
                    ch.name.lower() == channel.lower()
                ):
                    members = ctx.author.voice.channel.members
                    for member in members:
                        await member.move_to(ch)
                    return await ctx.send("*⃣ | Перемещен в {}".format(ch.name))
            return await ctx.send("Канал с таким именем не найден")

    @hybrid_command(
        name="prefix",
        pass_context=True,
        help="Команда для установки префикса бота",
        usage="prefix [префикс]",
    )
    @has_permissions(administrator=True)
    async def pref_(self, ctx, pref=None):
        if not pref:
            prefixes = await self.bot.get_prefix(ctx.message)
            sid = str(self.bot.user.id)
            for pr in prefixes:
                if sid not in pr:
                    return await ctx.send("Текущий префикс: {}".format(pr))
            return await ctx.send("Префикса не будет")

        if not ctx.guild:
            return await ctx.send("Нельзя установить префикс вне сервера")
        await self.bot.sql_client.sql_req(
            "INSERT INTO server_data (id, prefix) VALUES (%s, %s) ON DUPLICATE KEY UPDATE prefix=%s",
            ctx.guild.id,
            pref,
            pref,
        )
        return await ctx.send("Префикс установлен на {}".format(pref))

    @hybrid_command(
        name="ping",
        pass_context=True,
        help="Команда для проверки жизнеспособности бота",
    )
    async def ping_(self, ctx):
        embed = Embed(color=Color.dark_purple(), description="Pong")
        ts = time()
        msg = await ctx.send(embed=embed)
        tm = (time() - ts) * 1000
        embed.description = "{:.2f}ms".format(tm)
        return await msg.edit(embed=embed)

    @hybrid_command(
        name="exec",
        pass_context=True,
        help="Не трогай, она тебя сожрет",
        hidden=True,
        usage="exec <query>",
    )
    async def exec_(self, ctx, *, query):
        if str(ctx.author.id) == self.bot.config["discord"]["personal_id"]:
            exec(
                f"async def __ex(ctx): "
                + "".join(f"\n {line}" for line in query.split("\n"))
            )
            result = await locals()["__ex"](ctx)
            if result is None:
                result = ":)"
            return await ctx.send(result)


async def mod_setup(bot):
    await bot.add_cog(Moderation(bot))
