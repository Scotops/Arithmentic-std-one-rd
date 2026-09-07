/* Keep the page video in step with read-aloud play and pause events. */
(() => {
  'use strict';
  let activeAudio = null;
  let pauseTimer = 0;
  const nativePlay = HTMLMediaElement.prototype.play;
  const nativePause = HTMLMediaElement.prototype.pause;
  const pageVideo = () => {
    const shadowHost = document.querySelector('[data-sign-language-host="true"]');
    return shadowHost?.shadowRoot?.querySelector('video')
      || document.querySelector('#interface-container video, video');
  };
  const playVideo = () => {
    const video = pageVideo();
    if (video && video.paused) video.play().catch(() => {});
  };
  const pauseVideo = () => {
    const video = pageVideo();
    if (video && !video.paused) {
      video.dataset.adtNarrationSyncPause = 'true';
      video.pause();
      delete video.dataset.adtNarrationSyncPause;
    }
  };

  const onAudioPlay = (audio) => {
    window.clearTimeout(pauseTimer);
    activeAudio = audio;
    playVideo();
    window.setTimeout(playVideo, 80);
    window.setTimeout(playVideo, 240);
  };
  const onAudioPause = (audio) => {
    if (audio !== activeAudio) return;
    pauseTimer = window.setTimeout(() => {
      if (!activeAudio || activeAudio.paused) pauseVideo();
    }, audio.ended ? 300 : 80);
  };
  const onAudioEnded = (audio) => {
    if (audio !== activeAudio) return;
    pauseTimer = window.setTimeout(() => {
      if (!activeAudio || activeAudio.ended) {
        activeAudio = null;
        pauseVideo();
      }
    }, 300);
  };

  // The reader runtime constructs its narrator with `new Audio()` and does
  // not append that element to the document. Media events from a detached
  // element never reach document-level listeners, so intercept play/pause at
  // the media prototype as well as listening for ordinary in-DOM audio.
  HTMLMediaElement.prototype.play = function (...args) {
    const result = nativePlay.apply(this, args);
    if (this instanceof HTMLAudioElement) onAudioPlay(this);
    return result;
  };
  HTMLMediaElement.prototype.pause = function (...args) {
    const result = nativePause.apply(this, args);
    if (this instanceof HTMLAudioElement) onAudioPause(this);
    return result;
  };

  document.addEventListener('play', (event) => {
    if (event.target instanceof HTMLAudioElement) onAudioPlay(event.target);
  }, true);
  document.addEventListener('pause', (event) => {
    if (event.target instanceof HTMLAudioElement) onAudioPause(event.target);
  }, true);
  document.addEventListener('ended', (event) => {
    if (event.target instanceof HTMLAudioElement) onAudioEnded(event.target);
  }, true);
  window.setInterval(() => {
    if (activeAudio && !activeAudio.paused && !activeAudio.ended) {
      playVideo();
    } else if (activeAudio && activeAudio.ended) {
      onAudioEnded(activeAudio);
    }
  }, 200);
  window.ADT_MEDIA_SYNC = Object.freeze({
    active: () => Boolean(activeAudio && !activeAudio.paused && !activeAudio.ended),
    audio: () => activeAudio,
    video: () => pageVideo()
  });
})();
