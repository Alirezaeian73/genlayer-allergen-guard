import importlib.util
import json
import sys
import types
from pathlib import Path


class _Decorators:
    @staticmethod
    def write(function):
        return function

    @staticmethod
    def view(function):
        return function


class _UserError(Exception):
    pass


_fake_genlayer = types.ModuleType("genlayer")
_fake_genlayer.gl = types.SimpleNamespace(
    Contract=object,
    public=_Decorators(),
    vm=types.SimpleNamespace(UserError=_UserError),
)
_fake_genlayer.u256 = int
_fake_genlayer.TreeMap = dict

_contract_path = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "allergen_guard.py"
)

_previous_genlayer = sys.modules.get("genlayer")
sys.modules["genlayer"] = _fake_genlayer

try:
    _spec = importlib.util.spec_from_file_location(
        "allergen_guard_under_test",
        _contract_path,
    )
    _contract = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_contract)
finally:
    if _previous_genlayer is None:
        sys.modules.pop("genlayer", None)
    else:
        sys.modules["genlayer"] = _previous_genlayer


def test_clean_barcode_accepts_valid_barcode_and_trims_spaces():
    assert _contract._clean_barcode(" 3017620422003 ") == "3017620422003"


def test_clean_barcode_rejects_invalid_input():
    for value in ("1234567", "1234567x", "123456789012345", ""):
        try:
            _contract._clean_barcode(value)
        except _UserError:
            pass
        else:
            raise AssertionError(f"Expected invalid barcode to be rejected: {value!r}")


def test_clean_allergen_tag_normalizes_case_and_spaces():
    assert _contract._clean_allergen_tag(" EN:Milk ") == "en:milk"


def test_clean_allergen_tag_rejects_invalid_tags():
    for value in ("milk", "en:", "en:milk nuts", ""):
        try:
            _contract._clean_allergen_tag(value)
        except _UserError:
            pass
        else:
            raise AssertionError(f"Expected invalid tag to be rejected: {value!r}")


def test_extract_product_reads_and_sorts_allergen_tags():
    payload = {
        "status": 1,
        "product": {
            "code": "3017620422003",
            "product_name": "Nutella",
            "allergens_tags": ["en:soybeans", "en:milk", "en:milk"],
            "traces_tags": [],
        },
    }

    result = _contract._extract_product(
        json.dumps(payload),
        "3017620422003",
    )

    assert result == {
        "status": "OK",
        "barcode": "3017620422003",
        "product_name": "Nutella",
        "allergens_tags": ["en:milk", "en:soybeans"],
        "traces_tags": [],
    }


def test_extract_product_reports_missing_product():
    result = _contract._extract_product(
        json.dumps({"status": 0}),
        "3017620422003",
    )

    assert result == {
        "status": "NOT_FOUND",
        "barcode": "3017620422003",
    }


def test_extract_product_reports_incomplete_tag_data():
    payload = {
        "status": 1,
        "product": {
            "code": "3017620422003",
            "product_name": "Nutella",
            "allergens_tags": ["en:milk"],
        },
    }

    result = _contract._extract_product(
        json.dumps(payload),
        "3017620422003",
    )

    assert result == {
        "status": "DATA_INCOMPLETE",
        "barcode": "3017620422003",
    }


def test_extract_product_rejects_mismatched_barcode():
    payload = {
        "status": 1,
        "product": {
            "code": "0000000000000",
            "product_name": "Other product",
            "allergens_tags": [],
            "traces_tags": [],
        },
    }

    assert _contract._extract_product(
        json.dumps(payload),
        "3017620422003",
    ) is None


def test_extract_product_rejects_malformed_json():
    assert _contract._extract_product(
        "{not valid json",
        "3017620422003",
    ) is None


def test_extract_product_rejects_non_string_tags():
    payload = {
        "status": 1,
        "product": {
            "code": "3017620422003",
            "product_name": "Nutella",
            "allergens_tags": ["en:milk", 123],
            "traces_tags": [],
        },
    }

    assert _contract._extract_product(
        json.dumps(payload),
        "3017620422003",
    ) is None
