# anything2md

Python package and CLI for converting URLs or local documents into Markdown using Cloudflare Workers AI `toMarkdown()`.

## Install

```bash
pip install -e .
```

## Library Usage

```python
from anything2md import CloudflareCredentials, MarkdownConverter

credentials = CloudflareCredentials(
    account_id="<CLOUDFLARE_ACCOUNT_ID>",
    api_token="<CLOUDFLARE_API_TOKEN>",
)
converter = MarkdownConverter(credentials=credentials)

result = converter.convert_url("https://example.com/file.pdf")
print(result.markdown)

file_result = converter.convert_file("/path/to/file.pdf")
print(file_result.markdown)

converter.close()
```

## CLI Usage

```bash
export CLOUDFLARE_ACCOUNT_ID="your_account_id"
export CLOUDFLARE_API_TOKEN="your_api_token"

anything2md https://example.com/file.pdf
anything2md /path/to/file.pdf -o output.md
```
