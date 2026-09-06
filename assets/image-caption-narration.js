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

  const hideComponentImages = (container) => {
    container.querySelectorAll("img[data-id]").forEach((image) => {
      image.removeAttribute("data-id");
      image.setAttribute("alt", "");
      image.setAttribute("aria-hidden", "true");
    });
  };

  // Page 14 builds each group from repeated orange sprites. Narrating each
  // sprite once made the first row say "orange" repeatedly and left the later
  // rows without a description. Expose one accurate count for every row.
  const orangeExercise = content.querySelector("[data-section-id='pg014_sec001']");
  if (orangeExercise) {
    const rows = Array.from(orangeExercise.querySelectorAll(".grid"))
      .filter((row) => row.querySelector("img[data-id]"));
    const rowIds = [
      "pg014_im003", "pg014_n0013", "pg014_n0020", "pg014_n0027",
      "pg014_n0034", "pg014_n0041", "pg014_n0048", "pg014_n0055",
      "pg014_n0062"
    ];
    rows.slice(0, rowIds.length).forEach((row, index) => {
      const imageCell = row.querySelector("div");
      hideComponentImages(row);
      addCaption(imageCell || row, rowIds[index]);
    });
  }

  // Page 80 similarly assembles quantities from repeated rod sprites. Keep the
  // visual sprites decorative and narrate each complete quantity as a group.
  const placeValueExercise = content.querySelector("[data-section-id='pg080_sec002']");
  if (placeValueExercise) {
    const fallbackImage = placeValueExercise.querySelector(".sr-only img[data-id='pg080_im014']");
    const fallback = fallbackImage && fallbackImage.closest(".sr-only");
    if (fallback) {
      fallback.setAttribute("aria-hidden", "true");
      fallback.querySelectorAll("[data-id]").forEach((node) => node.removeAttribute("data-id"));
      fallback.querySelectorAll("img").forEach((image) => {
        image.alt = "";
        image.setAttribute("aria-hidden", "true");
      });
    }

    const groupSpecs = [
      ["img[data-id='pg080_im008']", "pg080_im008"],
      ["img[data-id='pg080_im011']", "pg080_im015"]
    ];
    groupSpecs.forEach(([selector, id]) => {
      const anchor = placeValueExercise.querySelector(selector);
      const cell = anchor && anchor.parentElement;
      if (!cell) return;
      hideComponentImages(cell);
      addCaption(cell, id);
    });
  }

  // The second subtraction row on page 43 accidentally reused the six-cup
  // picture. Crop the first bottle from the correct bottle artwork instead.
  const duplicateCupPictures = content.querySelectorAll("img[data-id='pg043_im001a_crop1']");
  if (duplicateCupPictures.length > 1) {
    const bottle = duplicateCupPictures[1];
    bottle.src = "images/pg043_im002a_crop1.png";
    bottle.alt = "One bottle.";
    bottle.setAttribute("data-id", "pg043_im002b_crop1");
    const quantity = bottle.parentElement && bottle.parentElement.querySelector(".sr-only");
    if (quantity) quantity.textContent = "1";
    Object.assign(bottle.style, {
      width: "55px",
      height: "126px",
      maxWidth: "none",
      objectFit: "none",
      objectPosition: "left top"
    });
  }
  const fourBottles = content.querySelector("img[data-id='pg043_im007_crop1']");
  if (fourBottles) fourBottles.alt = "Four bottles grouped together.";

  const narrated = new Set();
  content.querySelectorAll("img[data-id]").forEach((image) => {
    const id = image.getAttribute("data-id");
    if (!id) return;
    image.removeAttribute("data-id");
    if (narrated.has(id)) return;
    narrated.add(id);

    addCaption(image.parentElement, id);
  });
});
