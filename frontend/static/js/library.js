const libraryList = document.querySelector("#asset-list");
const libraryStatus = document.querySelector("#library-status");
const libraryPreview = document.querySelector("#asset-preview");
const libraryPrevious = document.querySelector("#library-previous");
const libraryNext = document.querySelector("#library-next");
const libraryRefresh = document.querySelector("#library-refresh");
let libraryPage = 1;
let libraryTotalPages = 1;
let librarySelectedId = null;
let libraryRequest = 0;

/**
 * 선택한 DB 원본을 이미지 또는 PDF로 표시한다.
 *
 * @param asset 저장이 완료된 원본 메타데이터.
 */
function selectAsset(asset) {
  librarySelectedId = asset.id;
  document.querySelector("#preview-title").textContent = asset.original_name;
  const download = document.querySelector("#preview-download");
  download.href = `/api/asset/${encodeURIComponent(asset.id)}/download`;
  download.hidden = false;
  const url = `/api/asset/${encodeURIComponent(asset.id)}/preview`;
  let content;
  if (asset.content_type === "image/png" || asset.content_type === "image/jpeg") {
    content = document.createElement("img");
    content.className = "asset-library__image";
    content.alt = asset.original_name;
    content.src = url;
    content.onerror = () => {
      if (librarySelectedId === asset.id) {
        libraryPreview.textContent = "원본 이미지를 표시하지 못했습니다. 내려받기를 이용해 주세요.";
      }
    };
  } else if (asset.content_type === "application/pdf") {
    content = document.createElement("iframe");
    content.className = "asset-library__pdf";
    content.title = `${asset.original_name} 원본 PDF`;
    content.src = url;
  } else {
    content = document.createElement("p");
    content.textContent = "이 형식은 원본 내려받기로 확인할 수 있습니다.";
  }
  libraryPreview.replaceChildren(content);
  libraryList.querySelectorAll("button").forEach((button) => {
    const selected = button.dataset.assetId === String(asset.id);
    button.setAttribute("aria-pressed", String(selected));
    button.classList.toggle("asset-library__item--selected", selected);
  });
}

/**
 * DB 목록을 갱신하고 새로고침 후에도 저장 원본을 조회한다.
 *
 * @param page 조회할 페이지 번호.
 * @param selectedId 업로드 직후 우선 표시할 원본 ID.
 * @returns 목록 조회와 선택 반영을 완료하는 비동기 작업.
 */
async function loadAssets(page = 1, selectedId = librarySelectedId) {
  const request = ++libraryRequest;
  libraryRefresh.disabled = libraryPrevious.disabled = libraryNext.disabled = true;
  libraryStatus.classList.remove("status--error");
  libraryStatus.textContent = "저장된 원본을 불러오고 있습니다…";
  libraryList.setAttribute("aria-busy", "true");
  try {
    const data = await fetchAssets(page);
    if (request !== libraryRequest) return;
    libraryPage = data.page;
    libraryTotalPages = Math.max(1, Math.ceil(data.total / data.page_size));
    const buttons = data.items.map((asset) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "asset-library__item";
      button.dataset.assetId = asset.id;
      button.setAttribute("aria-pressed", "false");
      const name = document.createElement("span");
      name.className = "asset-library__name";
      name.textContent = asset.original_name;
      const size = document.createElement("span");
      size.className = "asset-library__size";
      size.textContent = `${(asset.byte_size / 1024 / 1024).toFixed(2)} MiB`;
      button.append(name, size);
      button.addEventListener("click", () => selectAsset(asset));
      return button;
    });
    libraryList.replaceChildren(...buttons);
    libraryStatus.textContent = data.total
      ? `${data.total}개 원본 · ${libraryPage} / ${libraryTotalPages}페이지`
      : "아직 저장된 원본이 없습니다. 파일을 업로드해 주세요.";
    if (data.items.length) {
      selectAsset(data.items.find((asset) => asset.id === selectedId) || data.items[0]);
    }
  } catch (error) {
    if (request !== libraryRequest) return;
    libraryStatus.textContent = error.message;
    libraryStatus.classList.add("status--error");
  } finally {
    if (request === libraryRequest) {
      libraryRefresh.disabled = false;
      libraryPrevious.disabled = libraryPage <= 1;
      libraryNext.disabled = libraryPage >= libraryTotalPages;
      libraryList.setAttribute("aria-busy", "false");
    }
  }
}

libraryRefresh.addEventListener("click", () => loadAssets(libraryPage));
libraryPrevious.addEventListener("click", () => loadAssets(libraryPage - 1));
libraryNext.addEventListener("click", () => loadAssets(libraryPage + 1));
loadAssets();