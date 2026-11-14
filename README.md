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

Example:

```text
barcode: 3017620422003
allergen_tag: en:milk
