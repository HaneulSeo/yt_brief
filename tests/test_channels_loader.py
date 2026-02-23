from ytchannelpickcheck.channels_loader import load_channels_file, parse_channel_line


def test_parse_channel_id():
    r = parse_channel_line("UCabcdefghijklmnopqrstuvwxyz")
    assert r["channel_id"].startswith("UC")


def test_load_channels_txt_dedup(tmp_path):
    p = tmp_path / "channels.txt"
    p.write_text("https://www.youtube.com/channel/UCabcdefghijabcdefghijab\nhttps://www.youtube.com/channel/UCabcdefghijabcdefghijab\n", encoding="utf-8")
    rows = load_channels_file(p)
    assert len(rows) == 1
