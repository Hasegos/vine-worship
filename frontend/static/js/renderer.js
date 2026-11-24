/** @param {string} xml MusicXML. @param {HTMLElement} destination 새 SVG 생성 성공 후 교체할 영역. */
async function drawScore(xml, destination) {
  const staging = document.createElement("div");
  staging.className = "score-canvas render-staging";
  document.body.append(staging);
  try {
    const renderer = new opensheetmusicdisplay.OpenSheetMusicDisplay(staging, {
      backend: "svg",
      autoResize: false,
      drawTitle: true,
      drawPartNames: false,
      drawPartAbbreviations: false,
      newSystemFromXML: true,
      pageFormat: "Endless",
      defaultColorMusic: "#213c32",
    });
    await renderer.load(xml);
    renderer.render();
    destination.replaceChildren(...staging.childNodes);
  } finally {
    staging.remove();
  }
}