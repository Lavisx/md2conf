---
title: "Markdown child page"
---

<!-- confluence-page-id: 1933338 -->
<!-- confluence-space-key: ~hunyadi -->

If you are a user who wants to publish pages to Confluence, you should install the package [markdown-to-confluence](https://pypi.org/project/markdown-to-confluence/) from PyPI. If you are a developer who wants to contribute, you should clone the repository [md2conf](https://github.com/hunyadi/md2conf) from GitHub.

When exporting a directory hierarchy, these pages inherit a parent page ID, and the page will show up as a child page of its parent in Confluence's space overview.

When a child page without an explicit page ID is encountered, a Confluence page is automatically created, and its page ID is saved in the preamble of the Markdown document wrapped in a comment. Subsequently, synchronization will use the assigned page ID, and future changes to the parent/child relationship (e.g. moving the child page) will not be reflected.
