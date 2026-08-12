# Third-Party Source Notices

LychD is distributed under the [Mozilla Public License 2.0](LICENSE). The notices below apply to
third-party source incorporated into or adapted by particular LychD files; they do not replace the
project license.

## Altar Browser Bundle

The compiled Altar under `src/lychd/public/` contains third-party JavaScript and CSS dependencies.
Their package identities, declared license expressions, copyright notices, and license texts are
shipped with the browser artifact at
`src/lychd/public/THIRD_PARTY_NOTICES.txt`. The deterministic source inventory lives at
`clients/web/static/THIRD_PARTY_NOTICES.txt` and is regenerated from the pinned
`clients/web/package-lock.json` with:

```text
cd clients/web
npm run licenses
```

The corresponding rebuildable Altar source is distributed in `clients/web/` within the LychD source
distribution. The browser footer links the source revision and this notice inventory.

## Vessel Python Environment

The production Vessel image generates `/app/PYTHON_THIRD_PARTY_NOTICES.txt` from the exact Python
distributions installed in its locked virtual environment. The generator fails when a distribution
has no readable license material and no explicit same-project fallback. It also forbids
`psycopg-binary`: the Vessel uses pure-Python `psycopg` with Debian's dynamically loaded `libpq5`
instead of redistributing Psycopg's bundled native-library set. Debian system-package copyright
records remain under `/usr/share/doc`.

Regenerate an environment-specific inventory with:

```text
python scripts/generate_python_third_party_notices.py \
  --output PYTHON_THIRD_PARTY_NOTICES.txt \
  --forbid-distribution psycopg-binary
```

## Litestar Fullstack

Portions of the database-engine connection setup in `src/lychd/db/factory.py` are adapted from
[Litestar Fullstack](https://github.com/litestar-org/litestar-fullstack). The adapted source is
used under the following license:

```text
The MIT License (MIT)

Copyright (c) 2021, 2022, 2023, 2024, 2025 Litestar Org.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
