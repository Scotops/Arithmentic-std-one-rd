/* Make every image caption part of the standard read-aloud sequence. */
document.addEventListener("DOMContentLoaded", () => {
  const content = document.querySelector("#content");
  if (!content) return;

  // Remove prior generated captions before rebuilding the narration targets.
  content.querySelectorAll(".sr-only[data-id*='_im']").forEach((node) => node.remove());

  const addCaption = (container, id) => {
    if (!container || !id) return;
    const caption = document.createElement("span");
    caption.className = "sr-only adt-image-caption";
    caption.setAttribute("data-id", id);
    container.appendChild(caption);
  };

  // Repeated sprites are separate learning objects. Preserve every occurrence
  // in the speech sequence so a non-visual learner can count the same units as
  // a sighted learner without being told the total.
  content.querySelectorAll("img[data-id]").forEach((image) => {
    const id = image.getAttribute("data-id");
    if (!id) return;
    image.removeAttribute("data-id");
    addCaption(image.parentElement, id);
  });
});
