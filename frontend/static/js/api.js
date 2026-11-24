/** @param {string|null} key 목표 키. null이면 고정 원본을 조회한다. @returns {Promise<object>} 악보 응답. */
async function fetchScore(key) {
  const response = await fetch(
    key === null ? "/api/score" : `/api/score?key=${encodeURIComponent(key)}`,
  );
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "악보를 읽을 수 없습니다.");
  return result;
}