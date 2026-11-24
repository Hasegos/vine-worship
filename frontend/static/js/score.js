const target = document.querySelector("#target-key");
const status = document.querySelector("#status");
const download = document.querySelector("#download");
const print = document.querySelector("#print");
const referenceToggle = document.querySelector("#reference-toggle");
let activeKey = "D";
let originalHash = "";
let customZoom = false;

/**
 * 화면 폭에 맞추되 사용자가 지정한 확대 비율은 유지한다.
 */
function fitScore() {
  if (customZoom) return;
  const width = document.querySelector("#original-score").parentElement.clientWidth - 10;
  const percent = Math.max(30, Math.min(100, Math.floor((width / 1000) * 20) * 5));
  document.querySelector("#zoom").value = percent;
  document.querySelector("#zoom-value").textContent = `${percent}%`;
  document.documentElement.style.setProperty("--score-zoom", percent / 100);
}

/**
 * 변환 중 중복 조작을 막고 접근성 상태를 갱신한다.
 *
 * @param value 변환 중이면 true.
 */
function busy(value) {
  [target, download, print].forEach((control) => {
    control.disabled = value;
  });
  document.querySelector("#target-score").setAttribute("aria-busy", String(value));
}

/**
 * 고정 원본의 목표 키 악보를 표시하고 실패하면 기존 화면을 유지한다.
 *
 * @param key 변환할 목표 키.
 * @returns 화면 갱신 완료를 나타내는 비동기 작업.
 * @throws 원본 변경 또는 변환 결과 출력 실패.
 */
async function updateTarget(key) {
  busy(true);
  status.classList.remove("status--error");
  status.textContent = "전체 악보를 새로 그리고 있습니다…";
  try {
    const data = await fetchScore(key);
    if (data.source_hash !== originalHash) {
      throw new Error("원본 악보가 변경되었습니다. 페이지를 새로고침해 주세요.");
    }
    await drawScore(data.xml, document.querySelector("#target-score"));
    activeKey = key;
    target.value = key;
    document.querySelector("#target-key-label").textContent = key;
    document.querySelector("#target-badge").textContent = `${data.original_key} → ${key}`;
    const direction = data.semitones > 0 ? "위로" : "아래로";
    document.querySelector("#interval").textContent =
      data.semitones === 0 ? "원본과 같은 키" : `${Math.abs(data.semitones)}반음 ${direction}`;
    status.textContent = `${key}키 전체 악보 · 음표·코드 변환, 가사·리듬 유지`;
  } catch (error) {
    target.value = activeKey;
    status.textContent = error.message;
    status.classList.add("status--error");
    throw error;
  } finally {
    busy(false);
  }
}

target.addEventListener("change", () => {
  updateTarget(target.value).catch(() => {});
});
document.querySelector("#zoom").addEventListener("input", (event) => {
  customZoom = true;
  document.documentElement.style.setProperty("--score-zoom", event.target.value / 100);
  document.querySelector("#zoom-value").textContent = `${event.target.value}%`;
});
download.addEventListener("click", () => {
  window.location.href = `/score.musicxml?key=${encodeURIComponent(activeKey)}`;
});
print.addEventListener("click", () => {
  window.print();
});
window.addEventListener("resize", fitScore);
window.addEventListener("beforeprint", () => {
  const svg = document.querySelector("#target-score svg");
  if (svg) {
    const zoom = Math.min(700 / 1000, 1000 / Number(svg.getAttribute("height")));
    document.documentElement.style.setProperty("--print-zoom", zoom);
  }
});
referenceToggle.addEventListener("click", () => {
  const image = document.querySelector("#reference-image");
  image.hidden = !image.hidden;
  document.querySelector("#original-score").hidden = !image.hidden;
  referenceToggle.textContent = image.hidden ? "원본 이미지 보기" : "다시 그린 악보 보기";
});

(async () => {
  try {
    const original = await fetchScore(null);
    fitScore();
    originalHash = original.source_hash;
    document.querySelector("#song-title").textContent = original.title;
    document.querySelector("#source-kind").textContent = original.source_kind;
    document.querySelector("#original-key").value = original.original_key;
    document.querySelector("#source-key-label").textContent = original.original_key;
    document.querySelector("#measure-count").textContent = `${original.measure_count}마디`;
    if (original.reference_image) {
      document.querySelector("#reference-image").src = original.reference_image;
      referenceToggle.hidden = false;
    }
    await drawScore(original.xml, document.querySelector("#original-score"));
    await updateTarget(activeKey);
  } catch (error) {
    busy(true);
    status.textContent = `악보 표시를 완료하지 못했습니다. ${error.message}`;
    status.classList.add("status--error");
  }
})();