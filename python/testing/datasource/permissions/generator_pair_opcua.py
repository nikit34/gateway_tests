import json
import os


def _check_attr(owner_pair, format_pair, mode_pair):
    owner_fail = owner_pair not in ["server", "client"]
    mode_fail = mode_pair not in ["valid", "old", "bad", "short"]
    format_fail = format_pair not in ["DER", "PEM"]
    if owner_fail or mode_fail or format_fail:
        str_err = "Unsupported certificate generation:"
        if owner_fail:
            str_err += " owner"
        if mode_fail:
            str_err += " mode"
        if format_fail:
            str_err += " format"
        raise AttributeError(str_err)


def generate_pair_opcua(fixtures_path, owner_pair, format_pair, mode_pair, output_dir="", output_name=None):
    _check_attr(owner_pair, format_pair, mode_pair)
    with open(fixtures_path + "cert_key_storage.json", "r") as file:
        pair_templates = json.load(file)[mode_pair]
    if output_name is None:
        output_name = owner_pair
    cmd_gen_pair = pair_templates["cert"].format(
        fixtures_path=fixtures_path,
        type=owner_pair,
        fmt=format_pair,
        output_dir=output_dir,
        output_name=output_name
    )
    os.system(cmd_gen_pair)
    if format_pair == "DER":
        os.system(pair_templates["key"].format(fixtures_path=fixtures_path, type=owner_pair, output_dir=output_dir, output_name=output_name))
