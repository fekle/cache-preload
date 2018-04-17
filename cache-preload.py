#!/usr/bin/env python3

import time
import xml.etree.ElementTree as ET
from pathlib import Path
from random import randint

import click
import requests
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from slugify import slugify

mobile_useragent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1'
mobile_window_size = [375, 633]

desktop_useragent = None
desktop_window_size = [1920, 1080]


def get_urls(url, max_depth=32, current_depth=1):
    urls = []
    with requests.get(url, stream=True, timeout=10, allow_redirects=True) as r:
        try:
            # only use status 200
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                for item in root:
                    if item.tag.endswith('sitemap'):
                        # sitemap
                        if current_depth > max_depth:
                            print('==> warning: maximum depth of {:d} reached - will not continue to search for site maps'.format(current_depth))
                            break

                        for prop in item:
                            if prop.tag.endswith('loc'):
                                urls += get_urls(prop.text, max_depth, current_depth + 1)

                    elif item.tag.endswith('url'):
                        # url list
                        for prop in item:
                            if prop.tag.endswith('loc'):
                                urls.append(prop.text)
            else:
                print('==> "{:s}" returned status {:d}, skipping'.format(url, r.status_code))

            return sorted(set(urls))
        except (requests.RequestException, requests.ConnectionError, requests.Timeout) as e:
            print('==> "{:s}" failed with error "{:s}", skipping'.format(url, str(e)))


def do_test(browser, name, url, screenshot_dir):
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
        browser.get_screenshot_as_file(screenshot_paths[0])
        browser.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        browser.get_screenshot_as_file(screenshot_paths[1])


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
    urls = get_urls(url)

    if len(urls) <= 0:
        print('\n=> error: No urls found, exiting')
        exit(1)

    print('==> found {:d} urls'.format(len(urls)))

    for b in browsers:
        print('=> initializing firefox...')
        log_path = None

        if log_dir:
            log_path = log_dir.joinpath('{:s}.log'.format(b['name']))

        browser = get_browser(b['user_agent'], b['window_size'], geckodriver_path, log_path)

        for url in urls:
            try:
                print('=> visiting "{:s}" with browser "{:s}" ...'.format(url, b['name']), end='', flush=True)

                do_test(browser, b['name'], url, screenshot_dir)

                print(' done')
            except Exception as e:
                print('\n==> Error: "{:s}"\n==> skipping "{:s}"'.format(str(e), url))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        exit(1)
