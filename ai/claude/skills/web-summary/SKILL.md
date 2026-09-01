---
allowed-tools: WebFetch(domain:*)
description: "Generate comprehensive web page summary using WebFetch for specified URL"
argument-hint: [url]
disable-model-invocation: true
---

## Instructions

- Use the WebFetch tool to fetch and analyze the web page at $ARGUMENTS
  - If `$ARGUMENTS` is empty, ask for the URL with AskUserQuestion before proceeding
  - Respond in Japanese even when the page is in another language
- Format in markdown with bullet points
- Include the following sections:
  - **Page Title**: The title of the web page
  - **Summary**: Comprehensive overview of the main content
  - **Key Points**: Important information and takeaways
  - **Technical Details**: Any technical specifications, APIs, or implementation details mentioned
  - **Links/References**: Important links or references found in the content
  - **Additional Notes**: Any other relevant information or observations
