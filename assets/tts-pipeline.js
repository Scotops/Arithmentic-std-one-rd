/*
 * Deterministic read-aloud pipeline.
 *
 *  1. Extract addressable reading targets in DOM order.
 *  2. Remove duplicate image/caption nodes and non-reader content.
 *  3. Normalize text for diagnostics and TTS fallbacks.
 *  4. Hand a single ordered target list to the reader runtime.
 *
 * The ADT runtime normally plays pre-generated narration files.  This
 * pipeline deliberately works at the data-id level so its ordering is shared
 * by recorded audio and any browser SpeechSynthesis fallback.
 */
(() => {
  'use strict';

  const ANSWER_SELECTOR = [
    '[data-answer-key]', '[data-correct-answer]', '[data-solution]',
    '.answer-key', '.correct-answer', '.solution', '#quiz-correct-answers',
    '#quiz-explanations'
  ].join(',');

  const cardinal = (value) => {
    const ones = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
      'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'];
    const tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];
    const number = Number(value);
    if (!Number.isInteger(number) || number < 0 || number > 999) return String(value);
    if (number < 20) return ones[number];
    if (number < 100) return tens[Math.floor(number / 10)] + (number % 10 ? `-${ones[number % 10]}` : '');
    return `${ones[Math.floor(number / 100)]} hundred${number % 100 ? ` ${cardinal(number % 100)}` : ''}`;
  };

  const normalize = (value) => {
    let text = String(value || '')
      .replace(/<span[^>]*adt-blank-line[^>]*><\/span>/gi, ' dash ')
      .replace(/<[^>]+>/g, ' ')
      .replace(/&nbsp;/gi, ' ')
      .replace(/(?:\[\s*\]|_{2,})/g, ' dash ')
      .replace(/(\d+)\s*\/\s*(\d+)/g, '$1 over $2')
      // Some source pages contain a replacement character where the printed
      // subtraction sign was extracted.  Treat it as a mathematical minus
      // only when it occurs between numeric values; this keeps ordinary text
      // and names intact while making every subtraction question speakable.
      .replace(/(?<=\d)\s*�\s*(?=\d)/g, ' minus ')
      .replace(/[−–]/g, ' minus ')
      .replace(/(?<=\d)\s*-\s*(?=\d)/g, ' minus ')
      .replace(/\+\s*=/g, ' plus dash equals ')
      .replace(/-\s*=/g, ' minus dash equals ')
      .replace(/\+/g, ' plus ')
      .replace(/=/g, ' equals ')
      .replace(/÷/g, ' divided by ')
      .replace(/×/g, ' multiplied by ');
    text = text.replace(/(?<![A-Za-z])\d+(?![A-Za-z])/g, (match) => cardinal(match));
    // Collapse adjacent duplicate words and duplicate placeholders generated
    // by extraction from a repeated cell or image caption.
    text = text.replace(/\b([\p{L}\p{N}]+)(?:\s+\1\b)+/giu, '$1');
    text = text.replace(/\b(dash)(?:\s+dash\b)+/gi, 'dash');
    text = text.replace(/^(\d{1,3})\.$/, (_match, number) => `question number ${cardinal(number)}`);
    return text.replace(/\s+/g, ' ').replace(/\s+([,.;:!?])/g, '$1').trim();
  };

  const excluded = (element) => {
    if (!element || element.closest(ANSWER_SELECTOR)) return true;
    if (element.closest('[data-tts-exclude="true"], script, style, template')) return true;
    // Interactive exercises keep shuffled choices and answer text in hidden
    // markup. They are needed by the activity, but reading them aloud gives
    // away answers and makes the illustration order sound incorrect.
    for (let node = element; node && node !== document.documentElement; node = node.parentElement) {
      if (node.hidden || node.getAttribute('aria-hidden') === 'true') return true;
      const style = window.getComputedStyle?.(node);
      if (style?.display === 'none' || style?.visibility === 'hidden') return true;
    }
    return element.getAttribute('data-tts-role') === 'answer-key';
  };

  const extract = (root) => Array.from(root.querySelectorAll('[data-id]'))
    .filter((element) => !excluded(element));

  // Preserve every visible DOM occurrence. Repeated objects are meaningful
  // in a counting book even when they share one localized ID and audio clip.
  // image-caption-narration.js removes the ID from each visual image before
  // adding its one caption, so a visual/caption pair cannot be double-read.
  const deduplicate = (elements) => elements.filter((element) => element.getAttribute('data-id'));

  const summarizeMatrix = (container) => {
    const values = Array.from(container.querySelectorAll('img[alt], [data-tts-image-label]'))
      .map((node) => node.getAttribute('data-tts-image-label') || node.getAttribute('alt') || '')
      .map(normalize)
      .filter(Boolean);
    const runs = [];
    values.forEach((value) => {
      const prior = runs[runs.length - 1];
      if (prior && prior.value === value) prior.count += 1;
      else runs.push({ value, count: 1 });
    });
    return runs.map(({ value, count }) => count > 1 ? `${cardinal(count)} ${value}${/s$/i.test(value) ? '' : 's'}` : value);
  };

  const inspect = (root = document.getElementById('content'), texts = {}) => {
    if (!root) return [];
    return deduplicate(extract(root)).map((element, index) => {
      const id = element.getAttribute('data-id');
      return { index: index + 1, id, text: normalize(texts[id] ?? element.textContent ?? element.getAttribute('alt') ?? '') };
    });
  };

  let lockedVoice = null;

  const cancelPreviousSpeech = () => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  };

  // This reader normally uses the single pre-generated narrator recording.
  // If a browser falls back to SpeechSynthesis, select one voice once per
  // session and reuse that same SpeechSynthesisVoice for every utterance.
  const getLockedVoice = () => {
    if (!('speechSynthesis' in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    if (!voices.length) return lockedVoice;
    if (!lockedVoice || !voices.includes(lockedVoice)) {
      lockedVoice = voices.find((voice) => /^en(?:-|_)/i.test(voice.lang) && /guy|male/i.test(voice.name))
        || voices.find((voice) => /^en(?:-|_)/i.test(voice.lang))
        || voices[0];
    }
    return lockedVoice;
  };

  const speakFallbackQueue = (items, { rate = 1 } = {}) => {
    if (!('speechSynthesis' in window) || typeof SpeechSynthesisUtterance === 'undefined') return false;
    const phrases = items.map((item) => normalize(typeof item === 'string' ? item : item?.text)).filter(Boolean);
    if (!phrases.length) return false;
    cancelPreviousSpeech();
    const voice = getLockedVoice();
    let cursor = 0;
    const playNext = () => {
      if (cursor >= phrases.length) return;
      const utterance = new SpeechSynthesisUtterance(phrases[cursor++]);
      utterance.voice = voice;
      utterance.rate = rate;
      utterance.onend = playNext;
      window.speechSynthesis.speak(utterance);
    };
    playNext();
    return true;
  };

  window.ADT_TTS_PIPELINE = Object.freeze({
    extract,
    deduplicate,
    normalize,
    summarizeMatrix,
    inspect,
    cancelPreviousSpeech,
    getLockedVoice,
    speakFallbackQueue
  });
})();
