import DOMPurify from 'dompurify'

/**
 * Sanitize untrusted HTML string before rendering with v-html.
 * Uses DOMPurify to strip XSS vectors while keeping safe formatting tags.
 *
 * Allowed tags/attrs are intentionally broad to support markdown-rendered
 * previews and search-result highlights — only genuinely dangerous elements
 * (script, object, embed, etc.) are stripped.
 */
export function sanitize(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'ul', 'ol', 'li',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'strong', 'em', 'b', 'i', 'u', 's', 'del', 'ins',
      'a', 'code', 'pre', 'blockquote',
      'span', 'div', 'img',
      'mark', 'sub', 'sup',
    ],
    ALLOWED_ATTR: [
      'href', 'target', 'rel',
      'class', 'style',
      'src', 'alt', 'width', 'height',
      'colspan', 'rowspan',
    ],
    ALLOW_DATA_ATTR: false,
  })
}

export function useSanitize() {
  return { sanitize }
}
