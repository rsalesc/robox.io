import os
import pathlib
from typing import Any

import mechanize
from codefreaker.schema import Problem
from codefreaker.submitors.submitor import Submitor
from codefreaker.console import console

_SUBMITOR_KEY = "codeforces"


class Session:
    def __init__(self):
        self.br = mechanize.Browser()
        self.br.set_handle_robots(False)
        self.br.addheaders = [
            (
                "User-agent",
                "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1",
            )
        ]

    def select_form_by_id(self, id, forms):
        for form in forms:
            if form.attrs.get("id") == id:
                return form
        return None

    def select_form_by_class(self, cl, forms):
        for form in forms:
            if form.attrs.get("class") == cl:
                return form
        return None

    def login(self, handle, password):
        response = self.br.open("http://codeforces.com/enter")
        if not response.geturl().endswith("enter"):
            return
        form = self.select_form_by_id("enterForm", self.br.forms())
        if form is None:
            raise Exception("Login form was not found")

        form["handleOrEmail"] = handle
        form["password"] = password
        self.br.form = form
        response = self.br.submit()
        if response.geturl().endswith("enter"):
            raise Exception(
                "Login attempt was not successful. Check your credentials or your internet connection"
            )

    def submit(self, url: str, file: pathlib.Path, typeid: int):
        filename = os.path.abspath(file)
        self.br.open(url)
        form = self.select_form_by_class("submitForm", self.br.forms())
        if form is None:
            raise Exception("You are not logged in or problem does not exist")

        form["programTypeId"] = [str(typeid)]
        form.add_file(file.open(), "plain/text", filename)
        self.br.form = form
        response = self.br.submit()


class CodeforcesSubmitor(Submitor):
    def key(self) -> str:
        return _SUBMITOR_KEY

    def should_handle(self, problem: Problem) -> bool:
        return "codeforces.com/" in problem.url

    def submit(
        self,
        file: pathlib.Path,
        problem: Problem,
        submitor_config: Any,
        credentials: Any,
    ) -> bool:
        typeid = submitor_config["typeid"]
        handle = credentials["handle"]
        password = credentials["password"]

        session = Session()
        console.print(
            f"Trying to login with handle [item]{handle}[/item] in Codeforces."
        )
        try:
            session.login(handle, password)
        except Exception as e:
            console.print(f"[error]Failed to log in: {str(e)}[/error]")
            return False
        try:
            session.submit(problem.url, file, typeid)
        except Exception as e:
            console.print(f"[error]Failed to submit: {str(e)}[/error]")
            return False
        return True
