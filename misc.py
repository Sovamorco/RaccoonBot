from discord.ext import commands
import discord
import requests
from json import load
from random import choice
from html import unescape
import asyncio


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)

    @commands.command(name='raccoon', aliases=['racc'], help='Команда, которая сделает вашу жизнь лучше',
                      usage='?[racc|raccoon]')
    async def raccoon_(self, ctx):
        try:
            user = ctx.author
            with open('resources/raccoons.txt', 'r') as f:
                raccoons = load(f)
                raccoon = choice(raccoons)
            embed = discord.Embed()
            embed.set_image(url=raccoon)
            return await ctx.send('<@!{}>'.format(user.id), embed=embed)
        except Exception as e:
            await ctx.send('Ошибка: \n {}'.format(e))

    @commands.command(name='fact', aliases=['facts'], help='Команда, возвращающая рандомные факты',
                      usage='?[fact|facts]')
    async def facts_(self, ctx):
        try:
            user = ctx.author
            with open('resources/facts.txt', 'r') as f:
                facts = load(f)
                fact = choice(facts)
            embed = discord.Embed(description=fact)
            return await ctx.send('<@!{}>'.format(user.id), embed=embed)
        except Exception as e:
            await ctx.send('Ошибка: \n {}'.format(e))

    @commands.command(name='wikia', aliases=['wiki'], help='Команда для поиска статей на Fandom',
                      usage='?[wikia|wiki] <запрос>')
    async def wikia_(self, ctx, *, query=None):
        try:
            text_channel = ctx.message.channel
            if query is None:
                return await ctx.send('Использование: ?[wikia|wiki] <запрос>')
            apiurl = 'https://community.fandom.com/api/v1/Search/CrossWiki'
            user = ctx.message.author
            params = {
                'expand': 1,
                'query': query,
                'lang': 'ru,en',
                'limit': 10,
                'batch': 1,
                'rank': 'default'
            }
            result = requests.get(apiurl, params=params, timeout=0.5).json()
            if 'exception' in result.keys():
                return await ctx.send('Ничего не найдено')
            results = result['items']
            new_results = []
            embedValue = ''
            i = 0
            for result in results:
                if result:
                    if result['title']:
                        i += 1
                        embedValue += '{}. {}\n'.format(i, result['title'])
                        new_results.append(result)
            embed = discord.Embed(title='Выберите фэндом', description=embedValue)
            embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
            choice = await ctx.send(embed=embed)

            def verify(m):
                if m.content.isdigit():
                    return (0 <= int(m.content) <= len(results)) and (m.channel == text_channel) and (m.author == user)
                return False

            msg = await self.bot.wait_for('message', check=verify, timeout=30)
            if int(msg.content) == 0:
                return await choice.delete()
            result = new_results[int(msg.content) - 1]
            await choice.delete()
            if result['url'].endswith('/'):
                apiurl = '{}api/v1/'.format(result['url'])
            else:
                apiurl = '{}/api/v1/'.format(result['url'])
            params = {
                'query': query,
                'namespaces': '0,14',
                'limit': 1,
                'minArticleQuality': 0,
                'batch': 1
            }
            try:
                result = requests.get(apiurl+'Search/List', params=params, timeout=0.5).json()
            except Exception as e:
                await ctx.send('Ничего не найдено')
                return print(e)
            if 'exception' in result.keys():
                return await ctx.send('Ничего не найдено')
            page_id = result['items'][0]['id']
            params = {
                'ids': page_id,
                'abstract': 500,
                'width': 200,
                'height': 200
            }
            result = requests.get(apiurl+'Articles/Details', params=params, timeout=0.5).json()
            basepath = result['basepath']
            result = result['items'][str(page_id)]
            page_url = basepath+result['url']
            title = result['title']
            desc = unescape(result['abstract'])
            dims = result['original_dimensions']
            thumb = result['thumbnail']
            if dims is not None:
                width = dims['width']
                height = dims['height']
                if width <= 200:
                    params = {
                        'ids': page_id,
                        'abstract': 0,
                        'width': width,
                        'height': height
                    }
                else:
                    ratio = height/width
                    width = 200
                    height = ratio*width
                    params = {
                        'ids': page_id,
                        'abstract': 0,
                        'width': width,
                        'height': height
                    }
                result = requests.get(apiurl + 'Articles/Details', params=params, timeout=0.5).json()
                thumb = result['items'][str(page_id)]['thumbnail']
            embed = discord.Embed(title=title, url=page_url, description=desc)
            if thumb is not None:
                embed.set_thumbnail(url=thumb)
            return await ctx.send('<@!{}>'.format(user.id), embed=embed)
        except asyncio.TimeoutError:
            return
        except requests.exceptions.ConnectTimeout:
            await ctx.send('Не удалось подключиться к Wikia')
        except Exception as e:
            await ctx.send('Ошибка: \n {}'.format(e))


def misc_setup(bot):
    bot.add_cog(Misc(bot))
