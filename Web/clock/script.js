// 매초 현재 날짜와 시간을 갱신해 7-세그먼트 시계에 표시

const dateText = document.getElementById('dateText');
const timeText = document.getElementById('timeText');

// 한 자리 숫자를 두 자리로 맞추기 위한 0 패딩
// 실제 LCD 시계는 항상 고정 자리수로 표시되므로 잔상(88:88:88)과 위치가 정렬되어야 함
function pad(num) {
    return num.toString().padStart(2, '0');
}

function updateClock() {
    const now = new Date();

    const year = now.getFullYear();
    const month = pad(now.getMonth() + 1);
    const day = pad(now.getDate());

    // 24시간제 고정 — getHours()는 기본적으로 0~23 반환
    const hours = pad(now.getHours());
    const minutes = pad(now.getMinutes());
    const seconds = pad(now.getSeconds());

    dateText.textContent = `${year}년 ${month}월 ${day}일`;
    timeText.textContent = `${hours}:${minutes}:${seconds}`;
}

// 페이지 로딩 즉시 한 번 호출해야 초기 1초 동안 빈 화면이 보이지 않음
updateClock();

// setInterval은 정확히 1000ms 보장은 아니지만, 시계는 매 호출 시 Date.now()로 현재 시각을 다시 읽어오므로 누적 오차 없음
setInterval(updateClock, 1000);