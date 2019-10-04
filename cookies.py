from utils import form, get_prefix
from discord.ext import commands
import discord
import json
import asyncio
from random import randrange, randint


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


def add(userid, amt):
    cookies = json.load(open('resources/cookies.json', 'r'))
    cookies[str(userid)]['cookies'] += amt
    json.dump(cookies, open('resources/cookies.json', 'w'))


def get_cookies(userid):
    cookies = json.load(open('resources/cookies.json', 'r')).get(str(userid), None)
    if cookies is None:
        return None
    cookies = cookies['cookies']
    return cookies


class Cookies(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.add_cookies())

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError) and str(error.original):
            await ctx.send('Ошибка:\n' + str(error.original))

    async def add_cookies(self):
        while True:
            guilds = self.bot.guilds
            cookies = json.load(open('resources/cookies.json', 'r'))
            online = {}
            for guild in guilds:
                members = guild.members
                for member in members:
                    if member.status == discord.Status.online and not member.bot:
                        voice = False if member.voice is None else True
                        if (str(member.id) not in online.keys()) or voice:
                            online[str(member.id)] = {'nick': member.name, 'voice': voice}
            for user_id in online.keys():
                if str(user_id) in cookies.keys():
                    if online[user_id]['voice']:
                        cookies[user_id]['cookies'] += randrange(31, 35)
                    else:
                        cookies[user_id]['cookies'] += randrange(11, 15)
                else:
                    cookies[user_id] = {'id': int(user_id), 'name': online[user_id]['nick'],
                                        'cookies': randrange(289, 296)}
            json.dump(cookies, open('resources/cookies.json', 'w'))
            await asyncio.sleep(300)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.bot:
            cookies = json.load(open('resources/cookies.json', 'r'))
            if str(member.id) not in cookies.keys():
                cookies[str(member.id)] = {'id': member.id, 'name': member.name, 'cookies': randrange(289, 296)}
            json.dump(cookies, open('resources/cookies.json', 'w'))

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)
        user = ctx.author
        if not user.bot and not ctx.valid:
            cookies = json.load(open('resources/cookies.json', 'r'))
            if str(user.id) not in cookies.keys():
                cookies[str(user.id)] = {'id': user.id, 'name': user.name, 'cookies': randrange(289, 296)}
            else:
                cookies[str(user.id)]['cookies'] += randrange(10, 17)
            json.dump(cookies, open('resources/cookies.json', 'w'))

    @commands.command(name='cookies', aliases=['points'], help='Команда для отображения печенек',
                      usage='{}[cookies|points]')
    async def cookies_(self, ctx):
        user = ctx.author
        cookies = get_cookies(user.id)
        if cookies is None:
            return await ctx.send('У {} нет печенек'.format(user.mention))
        return await ctx.send(
            'У {} {:,} {}'.format(user.mention, cookies, form(cookies, ['печенька', 'печеньки', 'печенек'])))

    @commands.command(name='leaderboard', aliases=['lb'], help='Команда для отображения топа печенек',
                      usage='{}[lb|leaderboard]')
    async def leaderboard_(self, ctx):
        cookies = json.load(open('resources/cookies.json', 'r'))
        cookies = sorted(cookies.items(), key=lambda kv: kv[1]['cookies'], reverse=True)
        length = 10 if len(cookies) > 10 else len(cookies)
        embed = discord.Embed(color=discord.Color.dark_purple())
        embedValue = ''
        for i in range(length):
            amt = cookies[i][1]['cookies']
            embedValue += '{}. {}: {:,} {}\n\n'.format(i + 1, cookies[i][1]['name'], amt,
                                                       form(amt, ['печенька', 'печеньки', 'печенек']))
        embed.add_field(name='Глобальный топ', value=embedValue)
        embed.add_field(name='\u200b', value='\u200b')
        embedValue = ''
        i = 0
        for holder in cookies:
            if ctx.guild.get_member(holder[1]['id']) is not None:
                amt = holder[1]['cookies']
                embedValue += '{}. {}: {:,} {}\n\n'.format(i + 1, holder[1]['name'], amt,
                                                           form(amt, ['печенька', 'печеньки', 'печенек']))
                i += 1
                if i == length:
                    break
        embed.add_field(name='Топ сервера', value=embedValue)
        return await ctx.send('{}'.format(ctx.author.mention), embed=embed)

    @commands.command(name='blackjack', aliases=['bj'], help='Команда для игры в Блэкджек',
                      usage='{}[bj|blackjack] <ставка>')
    async def bj_(self, ctx, amt: int = 0):
        if amt <= 0:
            pref = await get_prefix(self.bot, ctx.message)
            return await ctx.send(f'Использование: {pref}[bj|blackjack] <ставка>')
        user = ctx.author
        cookies = get_cookies(user.id)
        if cookies is None:
            return await ctx.send('У вас нет печенек')
        if amt > cookies:
            return await ctx.send('У вас недостаточно печенек ({:,}, а необходимо {:,})'.format(cookies, amt))
        deck = gen_deck()
        add(user.id, -1 * amt)
        cookies = get_cookies(user.id)
        fst, snd, trd, frt = draw(deck), draw(deck), draw(deck), draw(deck)
        hand = [fst[1], trd[1]]
        split = [hand]
        dealer = [snd[1], frt[1]]
        embedValue = '''
        Дилер выдает вам {}
        Дилер берет {}
        Дилер выдает вам {}
        Дилер берет в закрытую'''.format(fst[0], snd[0], trd[0])
        embed = discord.Embed(color=discord.Color.dark_purple(), title='Ход игры', description=embedValue)
        msg = await ctx.send(embed=embed)
        if sum(split[0]) == 21:
            add(user.id, amt * 2)
            cookies = get_cookies(user.id)
            embed.description += '\n\nУ вас блэкджек, вы выиграли\nТеперь у вас {:,} {}'.format(cookies, form(cookies, [
                'печенька', 'печеньки', 'печенек']))
            return await msg.edit(embed=embed)
        if sum(dealer) == 21:
            cookies = get_cookies(user.id)
            embed.description += '\n\nУ дилера блэкджек, вы проиграли\nТеперь у вас {:,} {}'.format(cookies, form(cookies, ['печенька', 'печеньки', 'печенек']))
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
                add(user.id, -1*amt)
                spamt = [amt] * 2
        num = 0
        snum = ''
        for hand in split:
            if len(split) == 2:
                num += 1
                snum = ' '+str(num)
            while True:
                embed.description += '''
                
                Сумма карт у вас в руке{} - {}
                Хотите взять карту?
                (hit - взять, stand - пас)'''.format(snum, sum(hand))
                cookies = get_cookies(user.id)
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
                            cookies = get_cookies(user.id)
                            embed.description += '\n\nУ вас больше 21 очка, вы проиграли\nТеперь у вас {:,} {}'.format(cookies, form(cookies, ['печенька', 'печеньки', 'печенек']))
                            await msg.edit(embed=embed)
                            break
                if response.content.lower() == 'dd':
                    add(user.id, -1*amt)
                    if len(split) == 2:
                        # noinspection PyUnboundLocalVariable
                        spamt[num-1] *= 2
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
                            cookies = get_cookies(user.id)
                            embed.description += '\n\nУ вас больше 21 очка, вы проиграли\nТеперь у вас {:,} {}'.format(cookies, form(cookies, ['печенька', 'печеньки', 'печенек']))
                            await msg.edit(embed=embed)
                            break
                    embed.description += '\nСумма карт у вас в руке{} - {}'.format(snum, sum(hand))
                    break
                if response.content.lower() == 'stand':
                    embed.description += '\n\nВы оставили текущую руку\nСумма карт у вас в руке{} - {}'.format(snum, sum(hand))
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
                                add(user.id, spamt[i] * 2)
                    else:
                        add(user.id, amt * 2)
                    cookies = get_cookies(user.id)
                    embed.description += '\nУ дилера больше 21 очка, вы победили\nТеперь у вас {:,} {}'.format(cookies, form(cookies, ['печенька', 'печеньки', 'печенек']))
                    return await msg.edit(embed=embed)
        embed.description += '\nСумма карт в руке в дилера - {}'.format(sum(dealer))
        num = 0
        for hand in split:
            if len(split) == 2:
                num += 1
            if sum(hand) <= 21:
                if len(split) == 2:
                    embed.description += '\n\nРука {}'.format(num)
                    amt = spamt[num-1]
                if sum(dealer) == sum(hand):
                    add(user.id, amt)
                    cookies = get_cookies(user.id)
                    embed.description += '\nУ вас одинаковый счет, вам возвращена ставка\nТеперь у вас {:,} {}'.format(cookies, form(cookies, ['печенька', 'печеньки', 'печенек']))
                    await msg.edit(embed=embed)
                if sum(dealer) > sum(hand):
                    cookies = get_cookies(user.id)
                    embed.description += '\nУ вас меньше очков, чем у дилера\nВы проиграли\nТеперь у вас {:,} {}'.format(cookies, form(cookies, ['печенька', 'печеньки', 'печенек']))
                    await msg.edit(embed=embed)
                if sum(hand) > sum(dealer):
                    cookies = get_cookies(user.id)
                    add(user.id, amt * 2)
                    cookies = get_cookies(user.id)
                    embed.description += '\nУ вас больше очков, чем у дилера\nВы победили\nТеперь у вас {:,} {}'.format(cookies, form(cookies, ['печенька', 'печеньки', 'печенек']))
                    await msg.edit(embed=embed)


def cookies_setup(bot):
    bot.add_cog(Cookies(bot))
