/* Keep the page video in step with read-aloud play and pause events. */
(() => {
  'use strict';
  let activeAudio = null;
  let pauseTimer = 0;
  const pageVideo = () => document.querySelector('#interface-container video, video');
  const playVideo = () => {
    const video = pageVideo();
    if (video && video.paused) video.play().catch(() => {});
  };
  const pauseVideo = () => {
    const video = pageVideo();
    if (video && !video.paused) video.pause();
  };
  document.addEventListener('play', (event) => {
    if (!(event.target instanceof HTMLAudioElement)) return;
    window.clearTimeout(pauseTimer);
    activeAudio = event.target;
    playVideo();
    window.setTimeout(playVideo, 80);
    window.setTimeout(playVideo, 240);
  }, true);
  document.addEventListener('pause', (event) => {
    if (!(event.target instanceof HTMLAudioElement) || event.target !== activeAudio) return;
    pauseTimer = window.setTimeout(() => {
      if (!activeAudio || activeAudio.paused) pauseVideo();
    }, event.target.ended ? 300 : 80);
  }, true);
  document.addEventListener('ended', (event) => {
    if (!(event.target instanceof HTMLAudioElement) || event.target !== activeAudio) return;
    pauseTimer = window.setTimeout(() => {
      if (!activeAudio || activeAudio.ended) {
        activeAudio = null;
        pauseVideo();
      }
    }, 300);
  }, true);
  window.setInterval(() => {
    if (activeAudio && !activeAudio.paused && !activeAudio.ended) playVideo();
  }, 200);
  window.ADT_MEDIA_SYNC = Object.freeze({
    active: () => Boolean(activeAudio && !activeAudio.paused && !activeAudio.ended),
    video: () => pageVideo()
  });
})();
