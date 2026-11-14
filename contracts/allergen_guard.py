# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import hashlib
import json
import re


MAX_RESPONSE_LENGTH = 16000


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _clean_barcode(value: str) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError("Barcode must be text")
    barcode = value.strip()
    if re.fullmatch(r"[0-9]{8,14}", barcode) is None:
        raise gl.vm.UserError("Enter a barcode containing 8 to 14 digits")
    return barcode


def _clean_allergen_tag(value: str) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError("Allergen tag must be text, for example en:milk")
    tag = value.strip().lower()
    if re.fullmatch(r"en:[a-z0-9]+(?:-[a-z0-9]+)*", tag) is None:
        raise gl.vm.UserError(
            "Use an Open Food Facts tag such as en:milk or en:peanuts"
        )
    return tag


def _extract_product(payload_text: str, requested_barcode: str):
    if (
        not isinstance(payload_text, str)
        or not payload_text.strip()
        or len(payload_text) > MAX_RESPONSE_LENGTH
    ):
        return None

    try:
        payload = json.loads(payload_text)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    if payload.get("status") == 0:
        return {"status": "NOT_FOUND", "barcode": requested_barcode}

    if payload.get("status") != 1:
        return None

    product = payload.get("product")
    if not isinstance(product, dict):
        return None

    if product.get("code") != requested_barcode:
        return None

    allergens = product.get("allergens_tags")
    traces = product.get("traces_tags")

    if not isinstance(allergens, list) or not isinstance(traces, list):
        return {"status": "DATA_INCOMPLETE", "barcode": requested_barcode}

    if any(not isinstance(tag, str) for tag in allergens + traces):
        return None

    product_name = product.get("product_name", "")
    if not isinstance(product_name, str):
        return None

    return {
        "status": "OK",
        "barcode": requested_barcode,
        "product_name": product_name,
        "allergens_tags": sorted(set(allergens)),
        "traces_tags": sorted(set(traces)),
    }


class AllergenGuard(gl.Contract):
    check_count: u256
    checks: TreeMap[u256, str]

    def __init__(self):
        self.check_count = 0
        self.checks = TreeMap()

    @gl.public.write
    def check_allergen(self, barcode: str, allergen_tag: str) -> u256:
        barcode = _clean_barcode(barcode)
        allergen_tag = _clean_allergen_tag(allergen_tag)

        source_url = (
            "https://world.openfoodfacts.org/api/v2/product/"
            + barcode
            + ".json?fields=code,status,product_name,allergens_tags,traces_tags"
        )

        def evaluate_source() -> str:
            try:
                response = gl.nondet.web.get(source_url)
                response_text = response.body.decode("utf-8")
            except Exception:
                return _json({"status": "SOURCE_UNAVAILABLE"})

            product = _extract_product(response_text, barcode)
            if product is None:
                return _json({"status": "EXTRACTION_UNCLEAR"})

            if product.get("status") != "OK":
                return _json(product)

            product["source_sha256"] = hashlib.sha256(
                response_text.encode("utf-8")
            ).hexdigest()

            return _json(product)

        principle = (
            "Independently inspect the returned Open Food Facts JSON. Both results must "
            "agree on status and, for status OK, on the requested barcode, product name, "
            "allergens_tags, and traces_tags. Compare tag arrays as sets, ignoring order "
            "and duplicates. Ignore source hash differences only when all those product "
            "facts agree. Do not infer an allergen that is absent from the returned tags."
        )

        consensus_output = gl.eq_principle.prompt_comparative(
            evaluate_source,
            principle=principle,
        )

        try:
            if isinstance(consensus_output, str):
                observed = json.loads(consensus_output)
            elif isinstance(consensus_output, dict):
                observed = consensus_output
            else:
                observed = {"status": "EXTRACTION_UNCLEAR"}
        except Exception:
            observed = {"status": "EXTRACTION_UNCLEAR"}

        status = "UNCLEAR"
        product_name = ""
        source_allergens = []
        source_traces = []
        source_sha256 = ""

        if isinstance(observed, dict):
            observed_status = observed.get("status")

            if observed_status == "SOURCE_UNAVAILABLE":
                status = "SOURCE_UNAVAILABLE"

            elif observed_status == "NOT_FOUND":
                status = "PRODUCT_NOT_FOUND"

            elif observed_status == "DATA_INCOMPLETE":
                status = "DATA_INCOMPLETE"

            elif (
                observed_status == "OK"
                and observed.get("barcode") == barcode
                and isinstance(observed.get("product_name"), str)
                and isinstance(observed.get("allergens_tags"), list)
                and isinstance(observed.get("traces_tags"), list)
            ):
                product_name = observed.get("product_name", "")
                source_allergens = observed.get("allergens_tags", [])
                source_traces = observed.get("traces_tags", [])
                source_sha256 = observed.get("source_sha256", "")

                if (
                    all(isinstance(tag, str) for tag in source_allergens)
                    and all(isinstance(tag, str) for tag in source_traces)
                ):
                    source_allergens = sorted(set(source_allergens))
                    source_traces = sorted(set(source_traces))

                    if allergen_tag in source_allergens:
                        status = "DECLARED_ALLERGEN"
                    elif allergen_tag in source_traces:
                        status = "MAY_CONTAIN_TRACE"
                    else:
                        status = "NOT_LISTED"

        record_id = self.check_count

        record = {
            "id": int(record_id),
            "barcode": barcode,
            "product_name": product_name,
            "queried_allergen_tag": allergen_tag,
            "status": status,
            "source_allergens_tags": source_allergens,
            "source_traces_tags": source_traces,
            "source_name": "Open Food Facts",
            "source_url": source_url,
            "source_sha256": source_sha256,
            "notice": (
                "Open Food Facts is a community-maintained database. NOT_LISTED does not "
                "mean the product is allergen-free or safe. Product data may be incomplete "
                "or outdated. Always check the current package label and consult a qualified "
                "professional when needed. This record is informational, not medical advice."
            ),
        }

        self.checks[record_id] = _json(record)
        self.check_count += 1
        return record_id

    @gl.public.view
    def get_check(self, check_id: u256) -> str:
        return self.checks.get(check_id, "")

    @gl.public.view
    def get_check_count(self) -> u256:
        return self.check_count
