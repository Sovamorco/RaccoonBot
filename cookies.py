import asyncio
from asyncio import sleep
from itertools import islice
from random import randrange, randint

from discord import Status, Embed, Color
from discord.ext.commands import Cog, command, Bot

from utils import sform


def gen_deck():
    values = [('Туз', 11), ('2', 2), ('3', 3), ('4', 4), ('5', 5), ('6', 6), ('7', 7), ('8', 8), ('9', 9), ('10', 10),
              ('Вальта', 10), ('Даму', 10), ('Короля', 10)]
    types = ['Пик', 'Червей', 'Бубен', 'Треф']
    deck = []
    for value in values:
        for typ in types:
            deck.append((value[0] + ' ' + typ, value[1]))
    return deck


def draw(deck):
    return deck.pop(randint(0, len(deck) - 1))


class Cookies(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.loop.create_task(self.cookies_loop())

    async def cookies_loop(self):
        while True:
            try:
                guilds = self.bot.guilds
                online = {}
                for guild in guilds:
                    members = guild.members
                    for member in members:
                        if member.status == Status.online and not member.bot:
                            voice = bool(member.voice)
                            if (member.id not in online.keys()) or voice:
                                online[member.id] = {'nick': member.name, 'voice': voice}
                for user_id, user in online.items():
                    await self.add(user_id, randrange(31, 35) if user['voice'] else randrange(11, 15))
            except Exception as e:
                print(f'Exception in cookies loop:\n{e}')
            finally:
                await sleep(300)

    async def add(self, userid, amt):
        await self.bot.sql_client.sql_req(
            'INSERT INTO cookies (id, cookies) VALUES (%s, %s) ON DUPLICATE KEY UPDATE cookies=cookies+%s',
            userid, randrange(289, 296) + amt, amt,
        )

    async def get(self, userid):
        cookies = await self.bot.sql_client.sql_req('SELECT cookies FROM cookies WHERE id=%s', userid, fetch_one=True)
        if cookies is None:
            return None
        return cookies['cookies']

    @Cog.listener()
    async def on_member_join(self, member):
        if not member.bot:
            await self.add(member.id, 0)

    @Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)
        # if author is not a bot and message is not a command
        if not ctx.author.bot and not ctx.valid:
            await self.add(ctx.author.id, randrange(10, 17))

    @command(name='cookies', aliases=['points'], help='Команда для отображения печенек')
    async def cookies_(self, ctx):
        user = ctx.author
        cookies = await self.get(user.id)
        if cookies is None:
            return await ctx.send('У {} нет печенек'.format(user.mention))
        return await ctx.send(
            'У {} {:,} {}'.format(user.mention, cookies, sform(cookies, 'печенька')))

    @command(name='leaderboard', aliases=['lb'], help='Команда для отображения топа печенек')
    async def leaderboard_(self, ctx):
        cookies = await self.bot.sql_client.sql_req(
            'SELECT id, cookies FROM cookies ORDER BY cookies DESC',
            fetch_all=True,
        )
        embed = Embed(color=Color.dark_purple())

        async def get_lb_entry(pos, obj):
            user = await self.bot.fetch_user(obj['id'])
            return '{}. **{}**: {:,} {}'.format(pos + 1, user.name, obj['cookies'], sform(obj['cookies'], 'печенька'))

        global_lb = '\n'.join(await asyncio.gather(
            *[get_lb_entry(_pos, _obj) for _pos, _obj in enumerate(cookies[:10])]
        ))

        embed.add_field(name='Глобальный топ', value=global_lb, inline=True)

        local_entries = islice((entry for entry in cookies if ctx.guild.get_member(entry['id']) is not None), 10)
        local_lb = '\n'.join(await asyncio.gather(
            *[get_lb_entry(_pos, _obj) for _pos, _obj in enumerate(local_entries)]
        ))

        embed.add_field(name='Топ сервера', value=local_lb, inline=True)
        return await ctx.send('{}'.format(ctx.author.mention), embed=embed)

    @command(name='blackjack', aliases=['bj'],
             help='Команда для игры в Блэкджек\nПравила:\n- Дилер перестает брать на 17',
             usage='blackjack <ставка>')
    async def bj_(self, ctx, amt: int):
        if amt <= 0:
            return await ctx.send('Ставка должна быть положительным числом')
        user = ctx.author
        cookies = await self.get(user.id)
        if cookies is None:
            return await ctx.send('У вас нет печенек')
        if amt > cookies:
            return await ctx.send('У вас недостаточно печенек ({:,}, а необходимо {:,})'.format(cookies, amt))
        deck = gen_deck()
        await self.add(user.id, -1 * amt)
        cookies = await self.get(user.id)
        fst, snd, trd, frt = draw(deck), draw(deck), draw(deck), draw(deck)
        hand = [fst[1], trd[1]]
        split = [hand]
        dealer = [snd[1], frt[1]]
        embedValue = '''
        Дилер выдает вам {}
        Дилер берет {}
        Дилер выдает вам {}
        Дилер берет в закрытую'''.format(fst[0], snd[0], trd[0])
        embed = Embed(color=Color.dark_purple(), title='Ход игры', description=embedValue)
        msg = await ctx.send(embed=embed)
        if sum(split[0]) == 21:
            await self.add(user.id, amt * 2)
            cookies = await self.get(user.id)
            embed.description += '\n\nУ вас блэкджек, вы выиграли\nТеперь у вас {:,} {}'.format(cookies, sform(cookies,
                                                                                                               'печенька'))
            return await msg.edit(embed=embed)
        if sum(dealer) == 21:
            cookies = await self.get(user.id)
            embed.description += '\n\nУ дилера блэкджек, вы проиграли\nТеперь у вас {:,} {}'.format(cookies,
                                                                                                    sform(cookies,
                                                                                                          'печенька'))
            return await msg.edit(embed=embed)

        def verify(m):
            if m.content.lower() in ['hit', 'stand']:
                return m.author == user and m.channel == ctx.message.channel
            if m.content.lower() == 'dd' and cookies >= amt:
                return m.author == user and m.channel == ctx.message.channel
            return False

        def versplit(m):
            if m.content.lower() in ['да', 'нет']:
                return m.author == user and m.channel == ctx.message.channel
            return False

        if split[0][0] == split[0][1] and cookies >= amt:
            embed.description += '\n\nХотите разделить руку? (да/нет)\nАвтоматическая отмена через 300 секунд'
            await msg.edit(embed=embed)
            response = await self.bot.wait_for('message', check=versplit, timeout=300)
            if response.content.lower() == 'да':
                split = ([hand[0]], [hand[1]])
                await self.add(user.id, -1 * amt)
                spamt = [amt] * 2
        num = 0
        snum = ''
        for hand in split:
            if len(split) == 2:
                num += 1
                snum = ' ' + str(num)
            while True:
                embed.description += '''
                
                Сумма карт у вас в руке{} - {}
                Хотите взять карту?
                (hit - взять, stand - пас)'''.format(snum, sum(hand))
                cookies = await self.get(user.id)
                if cookies >= amt:
                    embed.description += '\nВы можете удвоить ставку (dd)'
                embed.description += '\nАвтоматическая отмена через 300 секунд'
                await msg.edit(embed=embed)
                response = await self.bot.wait_for('message', check=verify, timeout=300)
                if response.content.lower() == 'hit':
                    new = draw(deck)
                    hand.append(new[1])
                    embed.description += '\n\nВы взяли {}'.format(new[0])
                    if sum(hand) == 21:
                        embed.description += '\n\nУ вас 21 очко!'
                        await msg.edit(embed=embed)
                        break
                    if sum(hand) > 21:
                        if 11 in hand:
                            hand[hand.index(11)] = 1
                            await msg.edit(embed=embed)
                        else:
                            cookies = await self.get(user.id)
                            embed.description += '\n\nУ вас больше 21 очка, вы проиграли\nТеперь у вас {:,} {}'.format(
                                cookies, sform(cookies, 'печенька'))
                            await msg.edit(embed=embed)
                            break
                if response.content.lower() == 'dd':
                    await self.add(user.id, -1 * amt)
                    if len(split) == 2:
                        # noinspection PyUnboundLocalVariable
                        spamt[num - 1] *= 2
                    else:
                        amt *= 2
                    embed.description += '\n\nВы удвоили ставку'
                    new = draw(deck)
                    hand.append(new[1])
                    embed.description += '\nВы взяли {}'.format(new[0])
                    if sum(hand) == 21:
                        embed.description += '\n\nУ вас 21 очко!'
                        await msg.edit(embed=embed)
                        break
                    if sum(hand) > 21:
                        if 11 in hand:
                            hand[hand.index(11)] = 1
                            await msg.edit(embed=embed)
                        else:
                            cookies = await self.get(user.id)
                            embed.description += '\n\nУ вас больше 21 очка, вы проиграли\nТеперь у вас {:,} {}'.format(
                                cookies, sform(cookies, 'печенька'))
                            await msg.edit(embed=embed)
                            break
                    embed.description += '\nСумма карт у вас в руке{} - {}'.format(snum, sum(hand))
                    break
                if response.content.lower() == 'stand':
                    embed.description += '\n\nВы оставили текущую руку\nСумма карт у вас в руке{} - {}'.format(snum,
                                                                                                               sum(hand))
                    break
        if len(split) == 1 and sum(split[0]) > 21:
            return
        embed.description += '\n\nДилер открывает вторую карту - {}\n'.format(frt[0])
        await msg.edit(embed=embed)
        while sum(dealer) < 17:
            embed.description += '\nСумма карт в руке у дилера - {}'.format(sum(dealer))
            new = draw(deck)
            embed.description += '\nДилер берет {}'.format(new[0])
            dealer.append(new[1])
            if sum(dealer) > 21:
                if 11 in dealer:
                    dealer[dealer.index(11)] = 1
                    await msg.edit(embed=embed)
                else:
                    if len(split) == 2:
                        for i in range(len(split)):
                            if sum(split[i]) <= 21:
                                await self.add(user.id, spamt[i] * 2)
                    else:
                        await self.add(user.id, amt * 2)
                    cookies = await self.get(user.id)
                    embed.description += '\nУ дилера больше 21 очка, вы победили\nТеперь у вас {:,} {}'.format(cookies,
                                                                                                               sform(
                                                                                                                   cookies,
                                                                                                                   'печенька'))
                    return await msg.edit(embed=embed)
        embed.description += '\nСумма карт в руке в дилера - {}'.format(sum(dealer))
        num = 0
        for hand in split:
            if len(split) == 2:
                num += 1
            if sum(hand) <= 21:
                if len(split) == 2:
                    embed.description += '\n\nРука {}'.format(num)
                    amt = spamt[num - 1]
                if sum(dealer) == sum(hand):
                    await self.add(user.id, amt)
                    cookies = await self.get(user.id)
                    embed.description += '\nУ вас одинаковый счет, вам возвращена ставка\nТеперь у вас {:,} {}'.format(
                        cookies, sform(cookies, 'печенька'))
                    await msg.edit(embed=embed)
                if sum(dealer) > sum(hand):
                    cookies = await self.get(user.id)
                    embed.description += '\nУ вас меньше очков, чем у дилера\nВы проиграли\nТеперь у вас {:,} {}'.format(
                        cookies,
                        sform(cookies, 'печенька'))
                    await msg.edit(embed=embed)
                if sum(hand) > sum(dealer):
                    cookies = await self.get(user.id)
                    await self.add(user.id, amt * 2)
                    cookies = await self.get(user.id)
                    embed.description += '\nУ вас больше очков, чем у дилера\nВы победили\nТеперь у вас {:,} {}'.format(
                        cookies, sform(cookies, 'печенька'))
                    await msg.edit(embed=embed)


async def cookies_setup(bot):
    await bot.add_cog(Cookies(bot))
