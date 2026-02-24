from ytchannelpickcheck.transcript_client import TranscriptClient


class ObjectSnippet:
    def __init__(self, text, start=0.0, duration=0.0):
        self.text = text
        self.start = start
        self.duration = duration


class FakeTranscript:
    def __init__(self, language_code, is_generated, snippets):
        self.language_code = language_code
        self.is_generated = is_generated
        self._snippets = snippets

    def fetch(self):
        return self._snippets


class FakeTranscriptList:
    def __init__(self, transcript=None, generated=None):
        self._transcript = transcript
        self._generated = generated

    def find_transcript(self, langs):
        if self._transcript is None:
            raise RuntimeError("no transcript")
        return self._transcript

    def find_generated_transcript(self, langs):
        if self._generated is None:
            raise RuntimeError("no generated transcript")
        return self._generated


class FakeApi:
    def __init__(self, transcript_list):
        self._transcript_list = transcript_list

    def list(self, video_id):
        return self._transcript_list


def test_sni_get_supports_dict_and_object():
    client = TranscriptClient()
    as_dict = {"text": "alpha", "start": 1.2, "duration": 3.4}
    as_obj = ObjectSnippet("beta", start=2.3, duration=4.5)

    assert client._snip_get(as_dict, "text") == "alpha"
    assert client._snip_get(as_dict, "start") == 1.2
    assert client._snip_get(as_obj, "text") == "beta"
    assert client._snip_get(as_obj, "duration") == 4.5
    assert client._snip_get(as_obj, "missing", "x") == "x"


def test_fetch_joins_dict_snippets(monkeypatch):
    snippets = [{"text": "hello", "start": 0.0, "duration": 1.0}, {"text": "world", "start": 1.0, "duration": 1.0}]
    transcript = FakeTranscript("ko", False, snippets)
    client = TranscriptClient()
    monkeypatch.setattr(client, "api", FakeApi(FakeTranscriptList(transcript=transcript)))

    res = client.fetch("video-1")

    assert res["status"] == "success"
    assert res["lang"] == "ko"
    assert res["is_generated"] is False
    assert res["text"] == "hello world"


def test_fetch_joins_object_snippets(monkeypatch):
    snippets = [ObjectSnippet("hello", start=0.0, duration=1.0), ObjectSnippet("world", start=1.0, duration=1.0)]
    transcript = FakeTranscript("en", True, snippets)
    client = TranscriptClient()
    monkeypatch.setattr(client, "api", FakeApi(FakeTranscriptList(transcript=transcript)))

    res = client.fetch("video-2")

    assert res["status"] == "success"
    assert res["lang"] == "en"
    assert res["is_generated"] is True
    assert res["text"] == "hello world"
