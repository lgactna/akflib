"""
Interact with Microsoft Edge.
"""

from playwright.sync_api import sync_playwright, Playwright

import time

def run(playwright: Playwright):
    chromium = playwright.chromium # or "firefox" or "webkit".
    
    # do edge://version to see where the user data path is...
    #
    # https://playwright.dev/docs/api/class-browsertype#browser-type-launch-persistent-context-option-user-data-dir
    # "Note that Chromium's user data directory is the parent directory of the 
    # "Profile Path" seen at chrome://version."
    
    # also see https://stackoverflow.com/questions/74951776/python-playwright-wont-let-me-open-user-profile-other-than-default-profile
    # the profile directory is typically something like Default, Profile 2, Profile 3, etc
    args = ["--profile-directory=Profile 3"]

    # persistent contexts and non-persistent contexts are different, see
    # https://playwright.dev/docs/api/class-browsercontext
    # a persistent context actually writes to disk
    #
    # make sure that the profile in question is not in use when you run this, otherwise
    # you'll get some arcane error
    browser = chromium.launch_persistent_context(
        headless=False,
        user_data_dir="C:\\Users\\Kisun\\AppData\\Local\\Microsoft\\Edge\\User Data", # for some reason i need to add \Default??
        channel="msedge", # this is how you denote that something is an Edge browser,
        args=args
    )
    
    # browser = chromium.launch(headless=False, channel="msedge")
    page = browser.new_page()
    page.goto("http://example.com")
    # other actions...
    time.sleep(5)
    page.goto("https://www.google.com")
    
    time.sleep(10)
    
    browser.close()

with sync_playwright() as playwright:
    run(playwright)