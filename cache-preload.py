#!/usr/bin/env python3
import asyncio
import multiprocessing
import time
import xml.etree.ElementTree as ET
from functools import partial
from pathlib import Path
from random import randint

import aiohttp
import async_timeout
import click
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from slugify import slugify

mobile_useragent = 'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
mobile_window_size = [411, 731]
desktop_useragent = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
desktop_window_size = [1920, 1080]


async def load_sitemaps(url):
    async with aiohttp.ClientSession() as client:
        return await get_urls(client, url)


async def get_urls(client, url, max_depth=32, current_depth=1):
    urls = []

    try:
        async with async_timeout.timeout(10):
            async with client.get(url) as r:
                # only use status 200
                if r.status == 200:
                    root = ET.fromstring(await r.text())

                    for item in root:
                        if item.tag.endswith('sitemap'):
                            # sitemap
                            if current_depth > max_depth:
                                print('==> warning: maximum depth of {:d} reached - will not continue to search for site maps'.format(current_depth))
                                break

                            for prop in item:
                                if prop.tag.endswith('loc'):
                                    urls += await get_urls(client, prop.text, max_depth, current_depth + 1)

                        elif item.tag.endswith('url'):
                            # url list
                            for prop in item:
                                if prop.tag.endswith('loc'):
                                    urls.append(prop.text)

                else:
                    print('==> "{:s}" returned status {:d}, skipping'.format(url, r.status))

                return sorted(set(urls))
    except BaseException as ex:
        print(ex)
        print('==> "{:s}" failed with error, skipping'.format(url))


def do_test(browser, browser_meta, name, geckodriver_path, screenshot_dir, log_path, url):
    print('=> visiting "{:s}" with browser "{:s}" ...'.format(url, browser_meta['name']))

    screenshot_paths = None

    if screenshot_dir:
        slug = slugify(url)
        screenshot_paths = [
            str(Path(screenshot_dir, '{:s}-{:s}-top.png'.format(slug, name))),
            str(Path(screenshot_dir, '{:s}-{:s}-bottom.png'.format(slug, name)))
        ]

    browser.get(url)
    time.sleep(randint(500, 1000) / 1000)

    if screenshot_paths:
        browser.execute_script('window.scrollTo(0, 0)')
        time.sleep(randint(50, 100) / 1000)
        browser.get_screenshot_as_file(screenshot_paths[0])
        browser.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(randint(50, 100) / 1000)
        browser.get_screenshot_as_file(screenshot_paths[1])

    print('==> "{:s}" with browser "{:s}" done'.format(url, browser_meta['name']))


def get_browser(user_agent, window_size, geckodriver_path, log_path):
    browser_options = Options()
    browser_options.add_argument('--headless')

    if user_agent:
        browser_options.set_preference('general.useragent.override', user_agent)

    browser = webdriver.Firefox(log_path=str(log_path) if log_path else None, firefox_options=browser_options, executable_path=str(geckodriver_path))

    browser.set_window_size(window_size[0], window_size[1])
    return browser


@click.command(context_settings={'help_option_names': ['--help', '-h'], 'max_content_width': 256})
@click.argument('url', type=click.STRING)
@click.option('--desktop/--no-desktop', '-d/-nd', is_flag=True, default=True, show_default=True, help='enable desktop browser')
@click.option('--mobile/--no-mobile', '-m/-nm', is_flag=True, default=False, show_default=True, help='enable mobile browser')
@click.option(
    '--geckodriver-path',
    '-gp',
    type=click.Path(file_okay=True, dir_okay=False),
    default='/usr/bin/geckodriver',
    show_default=True,
    help='path to geckodriver binary'
)
@click.option('--screenshot-dir', '-sd', type=click.Path(exists=True, file_okay=False, dir_okay=True), help='save screenshots to directory')
@click.option('--log-dir', '-ld', type=click.Path(exists=True, file_okay=False, dir_okay=True), help='save logs to directory')
def main(mobile, desktop, url, geckodriver_path, screenshot_dir, log_dir):
    browsers = []

    if desktop:
        browsers.append({'name': 'desktop', 'window_size': desktop_window_size, 'user_agent': desktop_useragent})
    if mobile:
        browsers.append({'name': 'mobile', 'window_size': mobile_window_size, 'user_agent': mobile_useragent})

    if len(browsers) <= 0:
        print('=> error: no browsers enabled')
        exit(1)

    print('=> active browsers: "{:s}"'.format(', '.join(list(map(lambda x: x['name'], browsers)))))

    geckodriver_path = Path(geckodriver_path).resolve()

    if log_dir:
        log_dir = Path(log_dir).resolve()
        log_dir.mkdir(parents=True, exist_ok=True)
        print('=> will save logs to "{}"'.format(str(log_dir)))
    else:
        log_dir = None

    if screenshot_dir:
        screenshot_dir = Path(screenshot_dir).resolve().joinpath(str(int(time.time())))
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        print('=> will save screenshots to "{}"'.format(str(screenshot_dir)))
    else:
        screenshot_dir = None

    print('=> fetching all urls from sitemap on "{:s}" and its children...'.format(url))

    loop = asyncio.get_event_loop()
    urls = loop.run_until_complete(asyncio.gather(asyncio.ensure_future(load_sitemaps(url))))
    #urls = [['http://orf.at', 'https://duernberg.at', 'https://felixklein.net']]
    loop.close()

    if not urls or not urls[0]:
        print('=> error: No urls found, exiting')
        exit(1)

    if len(urls) <= 0 or len(urls[0]) <= 0:
        print('=> error: No urls found, exiting')
        exit(1)

    urls = urls[0]

    print('==> found {:d} urls'.format(len(urls)))

    pool = multiprocessing.Pool(processes=1)

    print('=> initializing firefox...')
    pool.map(partial(browser_run, urls, geckodriver_path, screenshot_dir, log_dir), browsers, 1)

    pool.close()
    pool.join()


def browser_run(urls, geckodriver_path, screenshot_dir, log_dir, browser):
    log_path = None

    if log_dir:
        log_path = log_dir.joinpath('{:s}.log'.format(browser['name']))

    b = get_browser(browser['user_agent'], browser['window_size'], geckodriver_path, log_path)

    for url in urls:
        do_test(b, browser, browser['name'], geckodriver_path, screenshot_dir, log_path, url)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        exit(1)
