#!/usr/bin/env python3

import sys
import argparse
import json
import os
import requests
import uuid
import tempfile
import webbrowser

try:
    from PIL import ImageGrab
except:
    ImageGrab = None

CONFIG_FILE = "accounts.json"


def normalize_instance(instance):

    instance = instance.strip()

    if instance.endswith("/"):
        instance = instance[:-1]

    if not instance.startswith("http"):
        instance = "https://" + instance

    return instance


def parse_ui(ui):

    user, inst = ui.split("@", 1)

    return user, normalize_instance(inst)


class MisskeyManager:

    def __init__(self):

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                self.config = json.load(f)
        else:
            self.config = {"accounts": []}

    def save(self):

        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    def find(self, instance, username):

        for acc in self.config["accounts"]:
            if acc["instance"] == instance and acc["username"] == username:
                return acc

        return None

    def remove(self, instance, username):

        before = len(self.config["accounts"])

        self.config["accounts"] = [
            a for a in self.config["accounts"]
            if not (a["instance"] == instance and a["username"] == username)
        ]

        self.save()

        return before != len(self.config["accounts"])

    # ------------------------------------------------
    # MiAuth authentication
    # ------------------------------------------------

    def authenticate(self, instance):

        instance = normalize_instance(instance)

        session_id = str(uuid.uuid4())

        permissions = [
            "write:notes",
            "write:drive"
        ]

        auth_url = (
            f"{instance}/miauth/{session_id}"
            f"?name=python-misskey-cli"
            f"&permission={','.join(permissions)}"
        )

        print("Open and authorize:")
        print(auth_url)

        webbrowser.open(auth_url)

        input("Press ENTER after authorization...")

        r = requests.post(
            f"{instance}/api/miauth/{session_id}/check"
        )

        if not r.ok:
            print(r.text)
            r.raise_for_status()

        data = r.json()

        if not data.get("ok"):
            print("Authorization failed")
            sys.exit(1)

        token = data["token"]
        user = data["user"]["username"]

        return {
            "instance": instance,
            "username": user,
            "token": token
        }

    def register(self, instance):

        acc = self.authenticate(instance)

        self.remove(acc["instance"], acc["username"])

        self.config["accounts"].append(acc)

        self.save()

        print("Registered:", acc["username"], "@", acc["instance"])

    def renew(self, instance, username):

        self.remove(instance, username)

        acc = self.authenticate(instance)

        self.config["accounts"].append(acc)

        self.save()

        print("Renewed:", username)


def upload_clipboard(account):

    if ImageGrab is None:
        print("Install pillow for clipboard support")
        return None

    img = ImageGrab.grabclipboard()

    if img is None:
        print("Clipboard empty")
        return None

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    img.save(tmp.name)

    with open(tmp.name, "rb") as f:

        r = requests.post(
            account["instance"] + "/api/drive/files/create",
            data={"i": account["token"]},
            files={"file": f}
        )

    os.unlink(tmp.name)

    r.raise_for_status()

    return r.json()["id"]


def compose(account, text, cw=None, visibility=None, clipboard=False):

    file_ids = []

    if clipboard:
        fid = upload_clipboard(account)
        if fid:
            file_ids.append(fid)

    payload = {
        "i": account["token"],
        "text": text
    }

    if cw:
        payload["cw"] = cw

    if visibility:
        payload["visibility"] = visibility

    if file_ids:
        payload["fileIds"] = file_ids

    r = requests.post(
        account["instance"] + "/api/notes/create",
        json=payload
    )

    if not r.ok:
        print(r.text)
        r.raise_for_status()

    print("Posted:", r.json()["createdNote"]["id"])


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("command", choices=["register","delete","compose","renew"])
    parser.add_argument("text", nargs="?")

    parser.add_argument("-u","--username")
    parser.add_argument("-i","--instance")
    parser.add_argument("-ui")

    parser.add_argument("--cw")
    parser.add_argument("--visibility","--visib")
    parser.add_argument("--cb", action="store_true")

    args = parser.parse_args()

    if args.ui:
        username, instance = parse_ui(args.ui)
    else:
        username = args.username
        instance = normalize_instance(args.instance)

    manager = MisskeyManager()

    if args.command == "register":
        manager.register(instance)

    elif args.command == "delete":
        if manager.remove(instance, username):
            print("Account removed")
        else:
            print("Account not found")

    elif args.command == "renew":
        manager.renew(instance, username)

    elif args.command == "compose":

        acc = manager.find(instance, username)

        if not acc:
            print("Account not registered")
            sys.exit(1)

        compose(
            acc,
            args.text,
            cw=args.cw,
            visibility=args.visibility,
            clipboard=args.cb
        )


if __name__ == "__main__":
    main()
