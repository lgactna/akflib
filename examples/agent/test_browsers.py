import logging
import os
import time
from pathlib import Path

from playwright.sync_api import Playwright, sync_playwright

logger = logging.getLogger(__name__)


def run(playwright: Playwright) -> None:
    chromium = playwright.chromium  # or "firefox" or "webkit".

    # do edge://version to see where the user data path is...
    #
    # https://playwright.dev/docs/api/class-browsertype#browser-type-launch-persistent-context-option-user-data-dir
    # "Note that Chromium's user data directory is the parent directory of the
    # "Profile Path" seen at chrome://version."

    # also see https://stackoverflow.com/questions/74951776/python-playwright-wont-let-me-open-user-profile-other-than-default-profile
    # the profile directory is typically something like Default, Profile 2, Profile 3, etc
    args = ["--profile-directory=Default"]

    # persistent contexts and non-persistent contexts are different, see
    # https://playwright.dev/docs/api/class-browsercontext
    # a persistent context actually writes to disk
    #
    # make sure that the profile in question is not in use when you run this, otherwise
    # you'll get some arcane error. also, this tends to involve blowing up some
    # microsoft edge processes in the background, probably because this thing
    # doesn't *actually* close the browser when you just click the X
    #
    # TODO: when writing this as a service, i'm guessing we should expose this attribute?
    # and then the user can use `browser.new_page()` and invoke page actions directly,
    # without having to conform to the limited options provided by the service itself
    #
    # when doing this, the API would have to indicate that this attribute exists and
    # the type that it has (after instantiation). as with similar projects, you would need
    # to create an "instance" of this API that initiates the RPyC connection (which allows
    # for instance attributes, like a remote `browser`, to be established)
    browser = chromium.launch_persistent_context(
        headless=False,
        user_data_dir="C:\\Users\\Kisun\\AppData\\Local\\Microsoft\\Edge\\User Data",  # for some reason i need to add \Default??
        channel="msedge",  # this is how you denote that something is an Edge browser,
        args=args,
    )

    # browser = chromium.launch(headless=False, channel="msedge")
    page = browser.new_page()
    page.goto("http://example.com")
    # other actions...
    time.sleep(5)
    page.goto("https://www.google.com")

    time.sleep(10)

    # all the locators:
    # https://playwright.dev/python/docs/locators#quick-guide

    # TODO: test if a browser can be made to be "persistent" in an RPyC service,
    # i.e. can there be two separate calls for opening and closing the browser,
    # such that the service maintains the state for a single browser instance?

    browser.close()


def get_appdata_local_path() -> Path:
    """
    Get the path to the AppData directory for the current user.
    """
    appdata_dir = os.getenv("LOCALAPPDATA")
    assert appdata_dir is not None

    if appdata_dir is None:
        raise Exception("Could not find the LOCALAPPDATA environment variable")

    return Path(appdata_dir).resolve()


if __name__ == "__main__":
    # with sync_playwright() as playwright:
    #     run(playwright)

    playwright = sync_playwright().start()
    browser = None

    profile = "Default"
    profile_path = get_appdata_local_path() / "Microsoft" / "Edge" / "User Data"

    chromium = playwright.chromium
    browser = chromium.launch_persistent_context(
        headless=False,
        user_data_dir=profile_path,
        channel="msedge",
        args=[f"--profile-directory={profile}"],
    )
