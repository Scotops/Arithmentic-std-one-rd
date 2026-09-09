/*
 * Read-aloud repairs for the printed-book presentation.
 *
 * The reader builds its playlist from source elements carrying data-id in DOM
 * order. Some pages include a second, responsive copy of the same table.
 * Only the copy visible at the current screen size belongs in the playlist.
 * This preserves the visual PDF page while removing duplicate narration.
 */
(() => {
  'use strict';

  const textFixes = {
    pg043_n0035: 'dash',
    pg043_n0060: 'dash',
    pg014_matrix_row_1: 'Seven oranges. Number one.',
    pg014_matrix_row_2: 'Four oranges. Number eight.',
    pg014_matrix_row_3: 'Two oranges. Number two.',
    pg014_matrix_row_4: 'Six oranges. Number seven.',
    pg014_matrix_row_5: 'Five oranges. Number four.',
    pg014_matrix_row_6: 'Three oranges. Number six.',
    pg014_matrix_row_7: 'Nine oranges. Number nine.',
    pg014_matrix_row_8: 'Eight oranges. Number five.'
  };

  // Correct malformed subtraction glyphs in the localized source before it
  // is placed in the page.  This repair applies only to a replacement
  // character between numbers, so it cannot alter a word or a proper name.
  const sanitizeLocalizedMath = (value) => String(value || '')
    .replace(/(?<=\d)\s*�\s*(?=\d)/g, ' - ');

  const pipeline = window.ADT_TTS_PIPELINE;

  const audioFixes = {
    pg043_n0035: 'pg043_n0035.revised.wav?v=audio-audit-20260824',
    pg043_n0060: 'pg043_n0060.revised.wav?v=audio-audit-20260824',
    pg100_n0070: 'pg100_n0070.revised.wav?v=audio-audit-20260824',
    pg100_n0075: 'pg100_n0075.revised.wav?v=audio-audit-20260824',
    pg100_n0079: 'pg100_n0079.revised.wav?v=audio-audit-20260824',
    pg100_n0083: 'pg100_n0083.revised.wav?v=audio-audit-20260824'
  };
  const questionLabelAudioFixes = {};
  const matrixDescriptionIds = new Set([
    'pg026_im010_seg001_v1_crop_v1', 'pg026_im010_seg002_v1_crop_v1',
    'pg026_im010_seg003_v1_crop_v1', 'pg026_im010_seg004_v1_crop_v1',
    'pg026_im010_seg005_v1', 'pg026_im010_seg006_v1_crop_v1',
    'pg026_im010_seg007_v1_crop_v1', 'pg026_im010_seg008_v1_crop_v1',
    'pg079_im016_seg001_v1_crop1', 'pg079_im016_seg002_v1_crop1',
    'pg085_im012_seg001_v1_crop_v1', 'pg085_im012_seg002_v1_crop_v1',
    'pg085_im012_seg003_v1_crop_v1', 'pg085_im012_seg004_v1_crop_v1',
    'pg085_im012_seg005_v1_crop_v1', 'pg085_im012_seg006_v1_crop_v1',
  ]);
  const matrixMathIds = new Set([
    'pg002_n0005', 'pg049_n0009', 'pg049_n0019', 'pg049_n0029', 'pg049_n0039',
    'pg049_n0049', 'pg049_n0012', 'pg049_n0022', 'pg049_n0032', 'pg049_n0042',
    'pg049_n0052', 'pg049_n0015', 'pg049_n0025', 'pg049_n0035', 'pg049_n0045',
    'pg049_n0055', 'pg055_n0016', 'pg055_n0020', 'pg055_n0025', 'pg055_n0029',
    'pg055_n0034', 'pg055_n0038', 'pg055_n0043', 'pg055_n0047', 'pg055_n0052',
    'pg055_n0056', 'pg055_n0061', 'pg055_n0065', 'pg055_n0070', 'pg055_n0074',
    'pg055_n0079', 'pg055_n0083'
  ]);
  // These chapter-banner images only repeat a title that immediately follows
  // as real page text. Keep the visible banner, but do not make a child hear
  // the title twice before the lesson begins.
  const repeatedChapterBannerIds = new Set([
    'pg016_im018',
    // The cover-style Revision Test banner repeats the two text headings
    // immediately below it.  Keep its visual treatment without reading the
    // test title a second time.
    'pg130_im018'
  ]);
  const guidedMatrixRows = {
    pg014_sec001: [
      'Seven oranges. Number one.',
      'Four oranges. Number eight.',
      'Two oranges. Number two.',
      'Six oranges. Number seven.',
      'Five oranges. Number four.',
      'Three oranges. Number six.',
      'Nine oranges. Number nine.',
      'Eight oranges. Number five.'
    ]
  };

  // A print matching grid can contain many repeated image sprites. Build one
  // audio-only row target for it, in visual left-to-right order, so it says
  // the number of objects then the numeral displayed in the right column.
  const registerGuidedMatrixRows = (root) => {
    const section = root?.querySelector('[data-section-id]');
    const rows = guidedMatrixRows[section?.getAttribute('data-section-id')];
    if (!rows) return;
    const grid = section.querySelector('.overflow-hidden.rounded-\\[28px\\]');
    const printedRows = grid ? Array.from(grid.children).slice(1) : [];
    printedRows.slice(0, rows.length).forEach((row, index) => {
      const target = document.createElement('span');
      target.className = 'sr-only adt-guided-matrix-row';
      target.setAttribute('data-id', `pg014_matrix_row_${index + 1}`);
      target.textContent = rows[index];
      row.prepend(target);
      row.querySelectorAll('[data-id]').forEach((element) => {
        if (element !== target) element.removeAttribute('data-id');
      });
    });
  };
  // These source pages include invisible duplicate operation labels. The
  // picture narration already says "add" and "equals", so omit only those
  // hidden duplicates while retaining the heading, picture and number fact.
  const guidedExampleComponentIds = new Set([
    'pg053_n0106', 'pg053_n0107', 'pg053_n0112', 'pg053_n0113'
  ]);

  const isVisibleForReading = (element) => {
    for (let node = element; node && node !== document.documentElement; node = node.parentElement) {
      if (getComputedStyle(node).display === 'none') return false;
    }
    return true;
  };

  const keepOnlyTheVisibleCopy = () => {
    const root = document.getElementById('content');
    if (!root) return;
    const all = Array.from(root.querySelectorAll('[data-id]'));
    const kept = new Set(pipeline ? pipeline.deduplicate(pipeline.extract(root)) : all);
    all.forEach((element) => {
      // Screen-reader labels embedded in print tables, hidden answer keys,
      // responsive copies, and duplicate image captions are not independent
      // pieces of book content.
      if (element.closest('label.sr-only')
        || repeatedChapterBannerIds.has(element.getAttribute('data-id'))
        || guidedExampleComponentIds.has(element.getAttribute('data-id'))
        || !kept.has(element)) element.removeAttribute('data-id');
    });
  };

  /*
   * The source book often prints a numbered exercise in several columns.
   * Its HTML therefore follows the print row (1, 7, 13, then 2, 8, 14),
   * while a child listening to the book needs the mathematical sequence
   * (1, 2, 3, ...).  Build an audio-only copy of the reading targets for
   * these grids.  The printed elements retain their exact appearance; only
   * the read-aloud playlist receives the reordered targets.
   */
  const questionNumber = (element) => {
    const match = (element.textContent || '').trim().match(/^(\d{1,3})\.(?:\s|$)/);
    return match ? Number(match[1]) : null;
  };

  /*
   * Some source pages print a red question marker (for example, "1.") as a
   * decorative span without a data-id.  The reader can only narrate elements
   * carrying data-id, which used to make it jump straight to the equation.
   * Give those standalone markers an audio-only identity before extraction.
   * The visual page is unchanged; the shared clips say "Question number one",
   * "Question number two", and so on.
   */
  const registerStandaloneQuestionLabels = (root) => {
    if (!root) return;
    const occurrences = new Map();
    root.querySelectorAll('span, p, div, td, th, li').forEach((element) => {
      if (element.hasAttribute('data-id') || element.children.length) return;
      const number = questionNumber(element);
      if (!number || number > 28) return;

      const parent = element.parentElement;
      const hasQuestionContent = Array.from(parent?.children || []).some((sibling) =>
        sibling !== element && (sibling.hasAttribute('data-id') || sibling.querySelector?.('[data-id]'))
      );
      if (!hasQuestionContent) return;

      const occurrence = (occurrences.get(number) || 0) + 1;
      occurrences.set(number, occurrence);
      const id = `adt_question_label_${number}_${occurrence}`;
      element.setAttribute('data-id', id);
      textFixes[id] = `${number}.`;
      questionLabelAudioFixes[id] = `question-number-${number}.mp3?v=matrix-question-labels-2`;
    });
  };

  // Most pages keep the printed question marker in its own source item.
  // Register its shared child-friendly clip before the reader fetches the
  // audio map, rather than letting the voice say an isolated digit.
  const registerPrintedQuestionLabels = (root) => {
    if (!root) return;
    root.querySelectorAll('[data-id]').forEach((element) => {
      const label = (element.textContent || '').trim().match(/^(\d{1,2})\.$/);
      if (label) {
        questionLabelAudioFixes[element.getAttribute('data-id')] =
          `question-number-${Number(label[1])}.mp3?v=matrix-question-labels-2`;
      }
    });
  };

  const orderedGridItems = (grid) => {
    // Some print layouts use one direct grid child per row.  Others wrap all
    // four cells of the row in a `contents` element.  Work from the actual
    // reading targets instead of the grid's direct children so both layouts
    // are handled consistently.
    const items = Array.from(grid.querySelectorAll('[data-id]'));
    const markers = items
      .map((element, index) => ({ element, index, number: questionNumber(element) }))
      .filter((item) => item.number !== null);

    // Only reorder a complete, unique run of question labels. This avoids
    // merging separate examples or ordinary number tables that happen to be
    // inside the same CSS grid.
    if (markers.length < 3 || new Set(markers.map((item) => item.number)).size !== markers.length) {
      return null;
    }
    const original = markers.map((item) => item.number);
    const sorted = [...markers].sort((a, b) => a.number - b.number || a.index - b.index);
    if (original.every((number, index) => number === sorted[index].number)) return null;

    // Keep each marker paired with all content up to the next marker. Thus,
    // "Question 2" is immediately followed by Question 2's equation, not a
    // question number from another printed column.
    const questions = markers.map((marker, index) => ({
      ...marker,
      items: items.slice(marker.index, markers[index + 1]?.index ?? items.length)
    }));
    const firstQuestion = markers[0].index;
    const beforeQuestions = items.slice(0, firstQuestion);
    return [...beforeQuestions, ...questions
      .sort((a, b) => a.number - b.number || a.index - b.index)
      .flatMap((question) => question.items)];
  };

  const makeNarrationTarget = (element) => {
    const isImage = element.tagName.toLowerCase() === 'img';
    const target = document.createElement(isImage ? 'img' : 'span');
    target.className = 'adt-reading-target';
    target.setAttribute('data-id', element.getAttribute('data-id'));
    if (isImage) {
      target.setAttribute('alt', element.getAttribute('alt') || '');
    } else {
      target.textContent = element.textContent || '';
    }
    return target;
  };

  // Printed revision tests often use two visual columns. Their source markup
  // can place question 2 after questions 10–20. Treat a page-wide, complete
  // sequence as one question list before considering nested layout grids, so
  // every question and its content stays together in numerical order.
  const pageWideQuestionOrder = (items) => {
    const markers = items
      .map((element, index) => ({ element, index, number: questionNumber(element) }))
      .filter((item) => item.number !== null);
    const numbers = markers.map((item) => item.number);
    const complete = markers.length >= 3
      && new Set(numbers).size === markers.length
      && numbers.every((number) => number >= 1 && number <= markers.length)
      && numbers.includes(1);
    if (!complete || numbers.every((number, index) => number === index + 1)) return null;
    const before = items.slice(0, markers[0].index);
    const questions = markers.map((marker, index) => ({
      ...marker,
      items: items.slice(marker.index, markers[index + 1]?.index ?? items.length)
    }));
    return [...before, ...questions
      .sort((left, right) => left.number - right.number)
      .flatMap((question) => question.items)];
  };

  const rebuildNarrationQueue = () => {
    const root = document.getElementById('content');
    if (!root) return;

    const sourceItems = pipeline ? pipeline.deduplicate(pipeline.extract(root)) : Array.from(root.querySelectorAll('[data-id]'));
    const excluded = new Set();
    const replacements = new Map();
    const ordered = [];

    const pageWide = pageWideQuestionOrder(sourceItems);
    if (pageWide) {
      ordered.push(...pageWide);
    }

    // Replace each out-of-order numbered grid with the same children, sorted
    // by its printed item number.  All remaining page content stays in DOM
    // order, which is already its intended reading order.
    // Exercises are usually CSS grids, but some source pages use a semantic
    // table or an unstyled activity section. Apply the same question-unit
    // ordering to each of those structures. A container is changed only when
    // it contains one complete, unique out-of-order question sequence.
    if (!pageWide) root.querySelectorAll('table, .grid, section[data-section-type]').forEach((grid) => {
      const replacement = orderedGridItems(grid);
      if (!replacement) return;
      const originalItems = Array.from(grid.querySelectorAll('[data-id]'));
      if (!originalItems.length) return;
      originalItems.forEach((element) => excluded.add(element));
      replacements.set(originalItems[0], replacement);
    });

    if (!pageWide) sourceItems.forEach((element) => {
      const replacement = replacements.get(element);
      if (replacement) ordered.push(...replacement);
      else if (!excluded.has(element)) ordered.push(element);
    });

    // Do not read the same element twice if a grid is nested in another grid.
    const unique = [];
    const seen = new Set();
    ordered.forEach((element) => {
      if (!seen.has(element)) {
        seen.add(element);
        unique.push(element);
      }
    });

    // A printed label such as “12.” is a question marker, not part of the
    // equation.  Send it to a shared clip which clearly says “Question
    // number twelve.”  The following source clip still reads the equation,
    // so visual layout and question content remain untouched.
    unique.forEach((element) => {
      const label = (element.textContent || '').trim().match(/^(\d{1,2})\.$/);
      if (label) questionLabelAudioFixes[element.getAttribute('data-id')] = `question-number-${Number(label[1])}.mp3?v=matrix-question-labels-1`;
    });

    if (!unique.length) return;
    // Save the final queue before removing source IDs. The visible page uses
    // its native print layout; these snapshots power safe console validation.
    const debugItems = unique.map((element, index) => ({
      index: index + 1,
      id: element.getAttribute('data-id'),
      text: pipeline?.normalize(element.textContent || element.getAttribute('alt') || '') || ''
    }));
    pipeline?.cancelPreviousSpeech();
    // Capture IDs before clearing the visual elements.  The visible page
    // becomes presentation-only; the hidden targets carry the audio IDs.
    const targets = unique.map(makeNarrationTarget);
    sourceItems.forEach((element) => element.removeAttribute('data-id'));
    const queue = document.createElement('div');
    queue.className = 'adt-reading-queue';
    queue.setAttribute('aria-hidden', 'true');
    queue.style.cssText = 'position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0';
    targets.forEach((target) => queue.appendChild(target));
    root.appendChild(queue);
    window.ADT_TTS_DEBUG = Object.freeze({
      queue: () => debugItems.map((item) => ({ ...item })),
      matrix: (selector) => pipeline?.summarizeMatrix(root.querySelector(selector)) || []
    });
  };

  const patchLocalizedFetches = () => {
    const fetchFromBook = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const url = typeof input === 'string' ? input : input?.url || '';
      const response = await fetchFromBook(input, init);
      if (!/content\/i18n\/en-US\/(texts|audios)\.json(?:[?#]|$)/.test(url)) return response;

      const data = await response.json();
      if (/texts\.json(?:[?#]|$)/.test(url)) {
        Object.keys(data).forEach((id) => { data[id] = sanitizeLocalizedMath(data[id]); });
        Object.assign(data, textFixes);
      }
      else {
        const descriptionAudioFixes = {};
        matrixDescriptionIds.forEach((id) => { descriptionAudioFixes[id] = `${id}.matrix-description-20260902.mp3?v=matrix-descriptions-1`; });
        const mathAudioFixes = {};
        matrixMathIds.forEach((id) => { mathAudioFixes[id] = `${id}.matrix-math-20260902.mp3?v=matrix-math-1`; });
        Object.assign(data, audioFixes, questionLabelAudioFixes, descriptionAudioFixes, mathAudioFixes);
      }
      return new Response(JSON.stringify(data), {
        status: response.status,
        statusText: response.statusText,
        headers: { 'Content-Type': 'application/json' }
      });
    };
  };

  // Image-caption-narration registers its DOM-ready handler before this
  // script.  Build the queue after that handler has replaced visual images
  // with their accessible captions, otherwise the queue can retain an old
  // generic image label instead of the complete child-friendly description.
  const initializeReadingQueue = () => {
    registerGuidedMatrixRows(document.getElementById('content'));
    registerStandaloneQuestionLabels(document.getElementById('content'));
    registerPrintedQuestionLabels(document.getElementById('content'));
    keepOnlyTheVisibleCopy();
    rebuildNarrationQueue();
  };
  // This script is intentionally loaded before the reader runtime. Register
  // labels and intercept the localized maps immediately, so the runtime sees
  // their text and "Question number …" audio on its first load.
  registerStandaloneQuestionLabels(document.getElementById('content'));
  registerPrintedQuestionLabels(document.getElementById('content'));
  patchLocalizedFetches();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeReadingQueue, { once: true });
  } else {
    initializeReadingQueue();
  }
})();
