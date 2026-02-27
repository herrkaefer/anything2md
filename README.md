# anything2md
[![CI](https://github.com/herrkaefer/anything2md/actions/workflows/ci.yml/badge.svg)](https://github.com/herrkaefer/anything2md/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/anything2md.svg)](https://pypi.org/project/anything2md/)
[![Python >=3.10](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://pypi.org/project/anything2md/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Python package and CLI for converting URLs or local documents into Markdown using Cloudflare Workers AI `toMarkdown()`.

## Install

From PyPI with `uv`:

```bash
uv add anything2md
```

Or from PyPI (pip):

```bash
pip install anything2md
```


### Cloudflare Token Setup

Create a Cloudflare API Token for the target account and include these permissions:

- `Workers AI` -- Read
- `Browser Rendering` -- Edit

## Usage

```python
import anything2md

mdconverter = anything2md(account_id="xxx", api_token="xxx")
result = mdconverter.transform("https://example.com")
result = mdconverter.transform("https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/somatosensory.pdf")
result = mdconverter.transform("https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/cat.jpeg")

# Browser Rendering advanced options for webpage URLs
result = mdconverter.transform(
    "https://example.com",
    url_strategy="browser",
    wait_until="networkidle2",
    reject_request_pattern=["/^.*\\.(css)$/", "/analytics/"],
)
print(result.markdown)
```

## Supported Formats

Based on Cloudflare docs, current supported extensions include:

`pdf`, `jpeg/jpg`, `png`, `webp`, `svg`, `html/htm`, `xml`, `csv`, `docx`, `xlsx`, `xlsm`, `xlsb`, `xls`, `et`, `ods`, `odt`, `numbers`

`url` via Browser Rendering Markdown endpoint.

## Local Usage

Install dependencies:

```bash
uv sync
```

```bash
export CLOUDFLARE_ACCOUNT_ID="your_account_id"
export CLOUDFLARE_API_TOKEN="your_api_token"

uv run anything2md https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/somatosensory.pdf
uv run anything2md https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/cat.jpeg -o output.md
uv run anything2md https://example.com
uv run anything2md https://example.com --url-strategy browser --wait-until networkidle2 --reject-request-pattern '/^.*\.(css)$/' --reject-request-pattern '/analytics/'
```

### Integration Test (Real Cloudflare)

If both `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` are set, integration tests automatically run real Cloudflare calls and validate that:

- `result.error` is empty
- `result.markdown` is non-empty

Optional test URL overrides:

- `ANYTHING2MD_TEST_PDF_URL`
- `ANYTHING2MD_TEST_IMAGE_URL`
- `ANYTHING2MD_TEST_WEB_URL`

## References

Cloudflare docs:
- Markdown Conversion overview: https://developers.cloudflare.com/workers-ai/features/markdown-conversion/
- API reference (`toMarkdown`): https://developers.cloudflare.com/api/resources/ai/methods/run/#to-markdown-conversion-to-markdown
- API reference (`supported formats`): https://developers.cloudflare.com/api/resources/ai/methods/run/#to-markdown-conversion-supported-formats
- Browser Rendering Markdown endpoint (URL input): https://developers.cloudflare.com/browser-rendering/rest-api/markdown-endpoint/
- Markdown for Agents (`Accept: text/markdown`): https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/

## License

MIT
