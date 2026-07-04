from app.data.watchlist_repository import parse_watchlist_entries_with_sectors, parse_watchlist_text


def test_parse_watchlist_text_keeps_tuple_compatibility_with_sector_tags():
    text = """
トヨタ (7203) 商社
任天堂,7974,ディフェンシブ
7011 - 三菱重工 - 防衛
"""

    assert parse_watchlist_text(text) == [
        ("トヨタ", "7203"),
        ("任天堂", "7974"),
        ("三菱重工", "7011"),
    ]


def test_parse_watchlist_entries_with_sectors_extracts_canonical_sector_tags():
    text = """
東京エレクトロン (8035) 半導体材料・装置
フジクラ (5803) 電線
ダイフク (6383) データセンター
三菱商事 (8058) 商社 資源
IHI (7013) 防衛 重工
"""

    entries = parse_watchlist_entries_with_sectors(text)

    assert [(entry.name, entry.code4, entry.sectors) for entry in entries] == [
        ("東京エレクトロン", "8035", ("半導体材料・装置",)),
        ("フジクラ", "5803", ("電線・電力インフラ",)),
        ("ダイフク", "6383", ("データセンター・電源、空調",)),
        ("三菱商事", "8058", ("商社・資源",)),
        ("IHI", "7013", ("防衛・重工",)),
    ]


def test_parse_watchlist_entries_with_sectors_allows_multiple_sector_tags():
    entries = parse_watchlist_entries_with_sectors("荏原 (6361) データセンター 水処理\n")

    assert entries[0].sectors == ("データセンター・電源、空調", "水処理・環境インフラ")


def test_parse_watchlist_entries_with_sectors_does_not_match_alias_inside_stock_name():
    entries = parse_watchlist_entries_with_sectors("三菱重工 (7011)\n三菱商事 (8058)\n")

    assert [(entry.name, entry.code4, entry.sectors) for entry in entries] == [
        ("三菱重工", "7011", ()),
        ("三菱商事", "8058", ()),
    ]
