from voltronic import __main__ as app


def test_find_hidraw_device_returns_first_valid_device(monkeypatch):
    class FakeInverter:
        instances = []

        def __init__(self, device):
            self.device = device
            self.closed = False
            FakeInverter.instances.append(self)

        def query(self, cmd, expected_len):
            assert cmd == "QMOD"
            return {"/dev/hidraw0": b"bad", "/dev/hidraw1": b"valid"}[self.device]

        def close(self):
            self.closed = True

    monkeypatch.setattr(app.glob, "glob", lambda pattern: [
        "/dev/hidraw1", "/dev/hidraw0",
    ])
    monkeypatch.setattr(app, "Inverter", FakeInverter)
    monkeypatch.setattr(app.parser, "parse_qmod", lambda payload: 1 if payload == b"valid" else 0)

    class Config:
        qmod = 5

    assert app._find_hidraw_device(Config()) == "/dev/hidraw1"
    assert [instance.device for instance in FakeInverter.instances] == [
        "/dev/hidraw0", "/dev/hidraw1",
    ]
    assert all(instance.closed for instance in FakeInverter.instances)


def test_find_hidraw_device_returns_none_when_no_device_is_valid(monkeypatch):
    class FakeInverter:
        def __init__(self, device):
            self.device = device
            self.closed = False

        def query(self, cmd, expected_len):
            return None

        def close(self):
            self.closed = True

    monkeypatch.setattr(app.glob, "glob", lambda pattern: ["/dev/hidraw0"])
    monkeypatch.setattr(app, "Inverter", FakeInverter)

    class Config:
        qmod = 5

    assert app._find_hidraw_device(Config()) is None
