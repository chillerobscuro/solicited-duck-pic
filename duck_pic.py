import os
import pickle
import smtplib
import time
import urllib.request
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

import praw
import schedule
import yaml
from PIL import Image


def run(message_to_send: str, save_loc: str = "duck.jpg", testing: bool = False) -> None:
    """
    Download top duck posts from reddit and send on schedule as defined in params.yaml
    """
    download_duck_post()
    send_messages(message_to_send, save_loc, testing)
    return


def download_duck_post(save_loc: str = "duck.jpg") -> None:
    """
    Get the top post from duck.reddit.com which we have not already sent and added to log.pkl
    """
    params = load_params()
    secret = params["reddit"]["secret"]
    me = params["reddit"]["me"]
    usr = params["reddit"]["user"]

    reddit = praw.Reddit(client_id=me, client_secret=secret, user_agent=usr)

    try:
        with open("log.pkl", "rb") as fp:
            log_list = pickle.load(fp)
    except FileNotFoundError:
        print("no log found!")
        log_list = []

    if len(log_list) > 50:
        log_list = log_list[-50:]

    for submission in reddit.subreddit("duck").top("week", limit=50):
        sub_url = submission.url
        if sub_url.split(".")[-1] in ["png", "jpg"] and sub_url not in log_list:
            data = urllib.request.urlretrieve(sub_url, save_loc)
            while (
                os.stat(save_loc).st_size > 500000
            ):  # halve file size until less than 500Mb
                im = Image.open(save_loc)
                if im.mode == "RGBA":
                    print("removing alpha channel")
                    im = im.convert("RGB")
                print(f"size before shrinkage: {os.stat(save_loc).st_size} / {im.size}")
                resize_to = (im.size[0] // 2, im.size[1] // 2)
                im.thumbnail(resize_to)
                im.save(save_loc)
                print(f"size after shrinkage: {os.stat(save_loc).st_size} / {im.size}")
            print(f"sending {sub_url}: {time.ctime()}")
            log_list.append(sub_url)
            with open("log.pkl", "wb") as fp:
                pickle.dump(log_list, fp)
            break


def send_messages(message_to_send: str, save_loc: str, testing: bool) -> None:
    """
    Send the message with attached duck pic
    """
    params = load_params()

    sender_email = params["email"]["sender_email"]
    # your gmail app password. Go to your google acct > Security > Signing in to Google > App passwords to generate a pw
    sender_email_pw = params["email"]["sender_email_pw"]
    contacts = params["contacts"]

    msg = MIMEMultipart()

    if testing:
        msg["To"] = contacts[0]
        contacts = contacts[:1]
    else:
        msg["To"] = ", ".join(contacts)
    msg["From"] = sender_email
    msg["Subject"] = message_to_send

    with open(save_loc, "rb") as fp:
        img = MIMEImage(fp.read())
    img.add_header("Content-ID", "<{}>".format(save_loc))
    msg.attach(img)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, sender_email_pw)
    server.sendmail(sender_email, contacts, msg.as_string())
    server.quit()


def load_params(file="params.yaml") -> Dict[str, Any]:
    with open(file) as f:
        params = yaml.safe_load(f)
    return params


def run_schedule(testing: bool = False) -> None:
    """
    Run the scheduled duck texts
    testing: set to True to send image to first contact right away
    """
    if testing:
        run(message_to_send="testing", testing=True)
    else:
        params = load_params()
        messages = params["timed_messages"]
        for tm in messages:
            msg = messages[tm]
            schedule.every().day.at(tm).do(run, message_to_send=msg)

        while True:
            schedule.run_pending()
            time.sleep(params["general"]["sleep_time_seconds"])


if __name__ == "__main__":
    print("Duck pic comin soon!")
    run_schedule(testing=False)
