from ytmp3.naming import build_stem, parse_track, safe_filename, strip_junk


def test_strip_junk_removes_bracketed_noise():
    assert strip_junk("Song Name (Official Music Video)") == "Song Name"
    assert strip_junk("Song Name [HD] (Lyrics)") == "Song Name"
    assert strip_junk("Song Name | Official Video") == "Song Name"


def test_strip_junk_keeps_meaningful_brackets():
    assert strip_junk("Song Name (Radio Edit)") == "Song Name (Radio Edit)"


def test_parse_title_with_artist_separator():
    name = parse_track({"title": "Some Artist - Some Song (Official Video)"})
    assert name.artist == "Some Artist"
    assert name.title == "Some Song"


def test_parse_prefers_music_metadata():
    name = parse_track(
        {"title": "whatever", "track": "Real Title", "artist": "Real Artist, Other"}
    )
    assert (name.artist, name.title) == ("Real Artist", "Real Title")


def test_parse_falls_back_to_topic_channel():
    name = parse_track({"title": "Just A Song", "uploader": "Some Artist - Topic"})
    assert name.artist == "Some Artist"
    assert name.title == "Just A Song"


def test_featuring_is_split_out():
    name = parse_track({"title": "A - B (feat. C)"})
    assert (name.artist, name.title, name.featuring) == ("A", "B", "C")
    assert name.full_artist == "A feat. C"
    assert name.search_query == "A B"


def test_title_without_separator_has_no_artist():
    name = parse_track({"title": "Just A Song"})
    assert name.artist is None
    assert name.title == "Just A Song"


def test_safe_filename_strips_path_characters():
    assert safe_filename('AC/DC: "Live" <1>') == "AC_DC_ _Live_ _1_"
    assert safe_filename("   ") == "untitled"
    assert safe_filename("con") == "_con"
    assert len(safe_filename("x" * 500)) == 120


def test_build_stem_numbering():
    name = parse_track({"title": "A - B"})
    assert build_stem(name) == "A - B"
    assert build_stem(name, index=3, number=True) == "03 - A - B"
