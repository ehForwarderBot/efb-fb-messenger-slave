from efb_fb_messenger_slave import utils


def test_utils_get_value():
    source = {
        "first": ['a', 'b', 'c', 'd'],
        "second": {
            "inner": [
                {"entry": "name"},
                {"entry": "value"}
            ]
        }
    }
    assert utils.get_value(source, ('first', 0), "fallback") == "a"
    assert utils.get_value(source, ('second', "inner", 1, "entry"), "fallback") == "value"
    assert utils.get_value(source, ('second', 0), "fallback") == "fallback"
    assert utils.get_value(source, ('1', 0, 2), None) is None
