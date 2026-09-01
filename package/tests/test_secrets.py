"""Passwords must never end up in memory.

Cairn writes its trail to a file on disk. A password in that file is a password in a
backup, a sync folder, and eventually a support ticket. So a step remembers *that* it
types a password, never *which* one, and the value is looked up on the machine that runs
the replay.
"""

from __future__ import annotations

import json

import pytest
from tests.conftest import TASK, cold_run

from cairn.browser import Browser, Element, domain_of
from cairn.operations import Session, secret_name
from cairn.secrets import MissingSecret, env_var_name, known_fields, resolve, store
from cairn.store import CairnStore


class TestRecognisingASecret:
    def test_a_password_box_is_a_secret(self):
        field = Element(
            ref="e1", role="textbox", name="Password", tag="input", css="#p", type="password"
        )

        assert secret_name(field) == "password"

    def test_an_ordinary_box_is_not(self):
        field = Element(ref="e1", role="textbox", name="Email", tag="input", css="#e", type="email")

        assert secret_name(field) is None

    def test_nothing_is_not_a_secret(self):
        assert secret_name(None) is None


class TestNothingSecretIsWrittenDown:
    def test_the_password_is_absent_from_the_saved_trail(
        self, browser: Browser, store: CairnStore, demo_server: str
    ):
        """The test that matters. Search the whole stored trail for the password."""
        session = Session(browser, store)
        cold_run(session, demo_server)
        session.save(TASK, domain=domain_of(demo_server))

        written = json.dumps(store.load_playbook(domain_of(demo_server)).to_dict())

        assert "hunter2" not in written, "the password was written into memory"

    def test_the_step_still_knows_a_password_belongs_there(
        self, browser: Browser, store: CairnStore, demo_server: str
    ):
        session = Session(browser, store)
        cold_run(session, demo_server)
        playbook = session.save(TASK, domain=domain_of(demo_server))

        password_steps = [step for step in playbook.steps if step.secret]

        assert len(password_steps) == 1
        assert password_steps[0].secret == "password"
        assert password_steps[0].value is None, "the value must not be kept"

    def test_the_email_is_still_remembered(
        self, browser: Browser, store: CairnStore, demo_server: str
    ):
        """Only secrets are dropped. Ordinary values are what make replay work."""
        session = Session(browser, store)
        cold_run(session, demo_server)
        playbook = session.save(TASK, domain=domain_of(demo_server))

        assert any(step.value == "finance@acme.com" for step in playbook.steps)

    def test_act_tells_the_caller_it_did_not_remember(self, browser: Browser, demo_server: str):
        session = Session(browser)
        session.act("open", "goto", value=f"{demo_server}/")
        page = session.look()
        password = next(e for e in page["elements"] if e["name"] == "Password")

        outcome = session.act("type the password", "fill", ref=password["ref"], value="hunter2")

        assert outcome["secret"] == "password"
        assert "did not remember" in outcome["note"]

    def test_look_never_reports_what_is_in_a_password_box(self, browser: Browser, demo_server: str):
        browser.goto(f"{demo_server}/")

        snapshot = browser.snapshot()

        password = next(e for e in snapshot.elements if e.name == "Password")
        assert password.value == "(filled)", "it may say a value exists, never what it is"
        assert "hunter2" not in str(snapshot.to_dict())


class TestFindingTheSecretAtReplayTime:
    def test_an_environment_variable_is_used(self, monkeypatch):
        monkeypatch.setenv(env_var_name("acme.com", "password"), "from-the-environment")

        assert resolve("acme.com", "password") == "from-the-environment"

    def test_the_variable_name_is_predictable(self):
        assert env_var_name("billing.acme.com", "password") == (
            "CAIRN_SECRET_BILLING_ACME_COM_PASSWORD"
        )

    def test_a_secrets_file_is_used_when_there_is_no_variable(self, tmp_path):
        secrets = tmp_path / "secrets.json"
        store("acme.com", "password", "from-the-file", secrets_file=secrets)

        assert resolve("acme.com", "password", secrets_file=secrets) == "from-the-file"

    def test_the_environment_wins_over_the_file(self, tmp_path, monkeypatch):
        secrets = tmp_path / "secrets.json"
        store("acme.com", "password", "from-the-file", secrets_file=secrets)
        monkeypatch.setenv(env_var_name("acme.com", "password"), "from-the-environment")

        assert resolve("acme.com", "password", secrets_file=secrets) == "from-the-environment"

    def test_a_missing_secret_says_exactly_what_to_set(self, tmp_path):
        with pytest.raises(MissingSecret) as raised:
            resolve("acme.com", "password", secrets_file=tmp_path / "nothing.json")

        message = str(raised.value)
        assert "CAIRN_SECRET_ACME_COM_PASSWORD" in message
        assert "acme.com" in message

    def test_it_never_guesses(self, tmp_path):
        """Falling back to a blank or an old value would fail three steps later,
        somewhere confusing. Better to stop here."""
        with pytest.raises(MissingSecret):
            resolve("acme.com", "password", secrets_file=tmp_path / "nothing.json")

    def test_the_file_lists_names_but_never_values(self, tmp_path):
        secrets = tmp_path / "secrets.json"
        store("acme.com", "password", "top-secret", secrets_file=secrets)

        assert known_fields("acme.com", secrets_file=secrets) == ["password"]

    def test_a_broken_secrets_file_is_survived(self, tmp_path):
        secrets = tmp_path / "secrets.json"
        secrets.write_text("this is not json", encoding="utf-8")

        with pytest.raises(MissingSecret):
            resolve("acme.com", "password", secrets_file=secrets)


class TestReplayWithoutTheSecret:
    def test_replay_stops_and_explains(
        self, browser: Browser, store: CairnStore, demo_server: str, monkeypatch
    ):
        """A judge running this with no setup should get a clear instruction, not a crash."""
        from cairn.executor import Executor

        session = Session(browser, store)
        cold_run(session, demo_server)
        session.save(TASK, domain=domain_of(demo_server))

        domain = domain_of(demo_server)
        monkeypatch.delenv(env_var_name(domain, "password"), raising=False)
        monkeypatch.setattr(
            "cairn.secrets.SECRETS_FILE", tmp_missing := __import__("pathlib").Path("nowhere.json")
        )
        assert not tmp_missing.exists()

        with pytest.raises(MissingSecret) as raised:
            Executor(store, browser).run(domain, start_url=f"{demo_server}/")

        assert "never stores it" in str(raised.value)
