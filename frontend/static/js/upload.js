const uploadForm = document.querySelector("#upload-form");
const uploadFile = document.querySelector("#asset-file");
const uploadButton = document.querySelector("#upload-button");
const uploadCancel = document.querySelector("#upload-cancel");
const uploadProgress = document.querySelector("#upload-progress");
const uploadStatus = document.querySelector("#upload-status");
const assetDownload = document.querySelector("#asset-download");

/**
 * 원본 전송 중 중복 제출을 막고 취소·진행 표시를 조정한다.
 *
 * @param value 전송 중이면 true.
 */
function uploadBusy(value) {
  uploadButton.disabled = value;
  uploadFile.disabled = value;
  uploadCancel.hidden = !value;
  uploadProgress.hidden = !value;
  uploadForm.setAttribute("aria-busy", String(value));
}

/**
 * 원본 파일을 변형 없이 저장하고 악보 인식과 구분해 결과를 표시한다.
 *
 * @param event 업로드 폼 제출 이벤트.
 */
function submitAsset(event) {
  event.preventDefault();
  const file = uploadFile.files[0];
  if (!file) return;
  const request = new XMLHttpRequest();
  uploadBusy(true);
  assetDownload.hidden = true;
  uploadProgress.value = 0;
  uploadStatus.classList.remove("status--error");
  uploadStatus.textContent = "원본을 DB에 전송하고 있습니다…";
  request.open("POST", `/api/asset?filename=${encodeURIComponent(file.name)}`);
  request.setRequestHeader("X-Vine-Upload", "1");
  request.responseType = "json";
  request.upload.onprogress = (progress) => {
    if (progress.lengthComputable) {
      uploadProgress.value = (progress.loaded / progress.total) * 100;
      if (progress.loaded === progress.total)
        uploadStatus.textContent = "전송 완료 · DB 저장 결과를 확인하고 있습니다…";
    }
  };
  request.onload = () => {
    const data = request.response;
    if (request.status !== 201 || !data) {
      uploadStatus.textContent = data?.detail || "원본을 저장하지 못했습니다.";
      uploadStatus.classList.add("status--error");
      return;
    }
    uploadStatus.textContent =
      `${data.original_name} · ` +
      `${data.byte_size.toLocaleString()}바이트 DB 저장 완료. ` +
      "자동 악보 인식은 아직 연결되지 않았습니다.";
    assetDownload.href = `/api/asset/${encodeURIComponent(data.id)}/download`;
    assetDownload.textContent = "저장한 원본 내려받기";
    assetDownload.hidden = false;
  };
  request.onerror = () => {
    uploadStatus.textContent =
      "연결이 끊겼습니다. 완료 여부가 불명확하므로 서버 상태를 확인해 주세요.";
    uploadStatus.classList.add("status--error");
  };
  request.onabort = () => {
    uploadStatus.textContent =
      "전송을 취소했습니다. 완료 응답 전 취소한 경우 서버 저장 여부를 확인해야 합니다.";
  };
  request.onloadend = () => {
    uploadBusy(false);
    uploadCancel.onclick = null;
  };
  uploadCancel.onclick = () => request.abort();
  request.send(file);
}

uploadForm.addEventListener("submit", submitAsset);