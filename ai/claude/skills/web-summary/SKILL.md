---
allowed-tools: WebFetch(domain:*),WebSearch
description: "Generate comprehensive web page summary using WebFetch for specified URL"
argument-hint: [url]
---

## Instructions

- Use the WebFetch tool to fetch and analyze the web page at $ARGUMENTS
  - Generate comprehensive summary suitable for understanding the content
  - Extract key information and main points
  - **IMPORTANT**: Always respond in Japanese regardless of the original language of the web page
- Format in markdown with bullet points
- Include the following sections:
  - **Page Title**: The title of the web page
  - **Summary**: Comprehensive overview of the main content
  - **Key Points**: Important information and takeaways
  - **Technical Details**: Any technical specifications, APIs, or implementation details mentioned
  - **Links/References**: Important links or references found in the content
  - **Additional Notes**: Any other relevant information or observations
