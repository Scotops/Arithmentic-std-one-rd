/* Keyboard access repairs from the ADT validation matrix.
 * X opens the table of contents, A opens settings, L opens language, and
 * Escape closes the currently open accessibility panel. The handler finds
 * the reader's controls by their accessible label, so it works with the
 * runtime's translated and responsive interface variants.
 */
(() => {
  'use strict';

  const isTyping = (node) => node && (
    node.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/i.test(node.tagName)
  );

  const controlFor = (terms) => Array.from(document.querySelectorAll('button, [role="button"]'))
    .find((element) => {
      const name = [
        element.getAttribute('aria-label'),
        element.getAttribute('title'),
        element.textContent
      ].filter(Boolean).join(' ').toLowerCase();
      return terms.some((term) => name.includes(term));
    });

  const activate = (terms) => {
    const control = controlFor(terms);
    if (!control) return false;
    control.click();
    return true;
  };

  document.addEventListener('keydown', (event) => {
    if (event.ctrlKey || event.altKey || event.metaKey || isTyping(event.target)) return;
    const key = event.key.toLowerCase();
    const actions = {
      x: ['table of contents', 'contents'],
      a: ['settings', 'accessibility'],
      l: ['language', 'translation']
    };

    if (event.key === 'Escape') {
      if (activate(['close accessibility', 'close panel', 'close'])) event.preventDefault();
      return;
    }
    if (actions[key] && activate(actions[key])) event.preventDefault();
  });
})();
