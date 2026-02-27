# anything2md

Python package and CLI for converting URLs or local documents into Markdown using Cloudflare Workers AI `toMarkdown()`.

Cloudflare docs:
- Markdown Conversion overview: https://developers.cloudflare.com/workers-ai/features/markdown-conversion/
- API reference (`toMarkdown`): https://developers.cloudflare.com/api/resources/ai/methods/run/#to-markdown-conversion-to-markdown
- API reference (`supported formats`): https://developers.cloudflare.com/api/resources/ai/methods/run/#to-markdown-conversion-supported-formats
- Browser Rendering Markdown endpoint (URL input): https://developers.cloudflare.com/browser-rendering/rest-api/markdown-endpoint/
- Markdown for Agents (`Accept: text/markdown`): https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/

## Install

From GitHub:

```bash
pip install "git+https://github.com/herrkaefer/anything2md.git"
```

For local development with `uv`:

```bash
uv sync
```

## Library Usage

```python
from anything2md import CloudflareCredentials, MarkdownConverter

credentials = CloudflareCredentials(
    account_id="<CLOUDFLARE_ACCOUNT_ID>",
    api_token="<CLOUDFLARE_API_TOKEN>",
)
converter = MarkdownConverter(credentials=credentials)

# PDF example from Cloudflare docs
result = converter.convert_url("https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/somatosensory.pdf")
print(result.markdown)

# Image example from Cloudflare docs
image_result = converter.convert_url("https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/cat.jpeg")
print(image_result.markdown)

# Webpage URL example:
# 1) try Accept: text/markdown (Markdown for Agents)
# 2) fallback to Cloudflare Browser Rendering Markdown endpoint
web_result = converter.convert_web_url("https://developers.cloudflare.com/")
print(web_result.markdown)

file_result = converter.convert_file("/path/to/file.pdf")
print(file_result.markdown)

# Query live supported formats from Cloudflare
formats = converter.supported_formats()
print(formats[0].extension, formats[0].mime_type)

converter.close()
```

## Supported Formats

Based on Cloudflare docs, current supported extensions include:

`pdf`, `jpeg/jpg`, `png`, `webp`, `svg`, `html/htm`, `xml`, `csv`, `docx`, `xlsx`, `xlsm`, `xlsb`, `xls`, `et`, `ods`, `odt`, `numbers`

Runtime check via API:

```bash
uv run python -c "from anything2md import CloudflareCredentials, MarkdownConverter; c=MarkdownConverter(CloudflareCredentials('<id>','<token>')); print([f.extension for f in c.supported_formats()]); c.close()"
```

## CLI Usage

```bash
export CLOUDFLARE_ACCOUNT_ID="your_account_id"
export CLOUDFLARE_API_TOKEN="your_api_token"

uv run anything2md https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/somatosensory.pdf
uv run anything2md https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/cat.jpeg -o output.md
uv run anything2md https://developers.cloudflare.com/
```

Run as module (alternative):

```bash
uv run python -m anything2md https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/somatosensory.pdf
```

Installed command (after `pip install` or from PyPI):

```bash
anything2md https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/somatosensory.pdf
```

URL strategy control:

```bash
# auto:
# - document URL -> ai/tomarkdown
# - webpage URL -> try Accept:text/markdown, fallback browser-rendering/markdown
uv run anything2md --url-strategy auto https://developers.cloudflare.com/

# force webpage URL flow (Accept:text/markdown first, fallback browser-rendering/markdown)
uv run anything2md --url-strategy browser https://example.com

# force remote download + ai/tomarkdown
uv run anything2md --url-strategy download https://example.com/sample.pdf
```
