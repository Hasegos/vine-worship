/**
 * 고정 원본 또는 목표 키의 악보 응답을 조회한다.
 *
 * @param key 고정 원본은 null, 변환 결과는 목표 키를 지정한다.
 * @returns 원본 정보와 전체 MusicXML을 담은 비동기 응답.
 * @throws 조회 실패 또는 응답 형식 오류.
 */
async function fetchScore(key) {
  const response = await fetch(
    key === null ? "/api/score" : `/api/score?key=${encodeURIComponent(key)}`,
  );
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "악보를 읽을 수 없습니다.");
  return result;
}