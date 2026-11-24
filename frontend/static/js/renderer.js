/**
 * 새 SVG 생성이 성공한 뒤에만 기존 악보를 교체한다.
 *
 * @param xml 전체 악보의 MusicXML.
 * @param destination 새 악보를 표시할 DOM 영역.
 * @returns 악보 교체 완료를 나타내는 비동기 작업.
 * @throws MusicXML 읽기 또는 악보 출력 실패.
 */
async function drawScore(xml, destination) {
  const staging = document.createElement("div");
  staging.className = "score-renderer score-renderer--staging";
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
    staging.querySelectorAll("svg").forEach((svg) => {
      svg.classList.add("score-renderer__svg");
    });
    destination.replaceChildren(...staging.childNodes);
  } finally {
    staging.remove();
  }
}