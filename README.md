# AllergenGuard

AllergenGuard is a GenLayer Intelligent Contract that checks whether a selected allergen appears in the Open Food Facts database entry for a product barcode.

It reports database labels only. It does not determine whether a product is medically safe.

## How it works

1. The caller provides a product barcode and an Open Food Facts allergen tag, such as `en:milk`.
2. The contract retrieves the product entry from the Open Food Facts API.
3. Independent evaluations compare the product code, product name, declared allergen tags, and trace tags.
4. The contract records the result, source URL, source response hash, and a safety notice on-chain.

## Possible results

- `DECLARED_ALLERGEN`: The selected tag appears in `allergens_tags`.
- `MAY_CONTAIN_TRACE`: The selected tag appears in `traces_tags`.
- `NOT_LISTED`: The selected tag was not found in either tag list. This does not mean the product is allergen-free or safe.
- `PRODUCT_NOT_FOUND`: The source did not return a product for the barcode.
- `DATA_INCOMPLETE`: The source response did not include the required tag fields.
- `SOURCE_UNAVAILABLE`: The data source could not be reached.
- `UNCLEAR`: The response could not be reliably interpreted.

## Contract interface

### `check_allergen(barcode, allergen_tag)`

Checks the selected tag and stores a record. The function returns the record ID.

Example inputs:

    barcode: 3017620422003
    allergen_tag: en:milk

### `get_check(check_id)`

Returns the stored record as a JSON string.

### `get_check_count()`

Returns the number of stored checks.

## Data source

Open Food Facts product API:

`https://world.openfoodfacts.org/api/v2/product/{barcode}.json`

Open Food Facts is a community-maintained database. Product data may be incomplete or outdated. Always check the current package label and consult a qualified professional when needed.

## Deployment and live check

- Contract address: [`0x310bC826d58c0dD04628ae30e94b5CfCc13C3Db1`](https://explorer-studio.genlayer.com/address/0x310bC826d58c0dD04628ae30e94b5CfCc13C3Db1)
- Deployment transaction: [`0x6b2e9e07383a1a952a237c1a4d874f946c33b5af893e02a701606b4620da580c`](https://explorer-studio.genlayer.com/tx/0x6b2e9e07383a1a952a237c1a4d874f946c33b5af893e02a701606b4620da580c)
- Live check transaction: [`0x3bc13969708f644cfc8705f293b80f18dc93f661d10c8d39df682f171a7bd18e`](https://explorer-studio.genlayer.com/tx/0x3bc13969708f644cfc8705f293b80f18dc93f661d10c8d39df682f171a7bd18e)

The recorded live example returned `DECLARED_ALLERGEN` for `en:milk` on barcode `3017620422003`. This reflects the source database response at the time of the check, not an independent laboratory test.

## Run local tests

    python -m pip install -r requirements-dev.txt
    python -m pytest -q

The local unit tests cover input validation and source-response parsing. The live contract call is linked above.

## Disclaimer

AllergenGuard is an informational software demonstration. `NOT_LISTED` is not a safety guarantee, and this project is not medical advice. Verify ingredients and allergen warnings on the product packaging.
