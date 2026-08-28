const API_BASE_URL =
    "http://127.0.0.1:8000";


const generateButton =
    document.getElementById(
        "generate-button"
    );

const explainButton =
    document.getElementById(
        "explain-button"
    );

const emptyState =
    document.getElementById(
        "empty-state"
    );

const scheduleContent =
    document.getElementById(
        "schedule-content"
    );

const scheduleList =
    document.getElementById(
        "schedule-list"
    );

const scheduleGrid =
    document.getElementById(
        "schedule-grid"
    );

const tabListView =
    document.getElementById(
        "tab-list-view"
    );

const tabGridView =
    document.getElementById(
        "tab-grid-view"
    );

const totalCredits =
    document.getElementById(
        "total-credits"
    );

const statusBox =
    document.getElementById(
        "status-box"
    );

const aiExplanation =
    document.getElementById(
        "ai-explanation"
    );

const studentName =
    document.getElementById(
        "student-name"
    );

const studentMajor =
    document.getElementById(
        "student-major"
    );

const studentSemester =
    document.getElementById(
        "student-semester"
    );


let currentSchedule = null;


/* =========================
   STUDENT
========================= */

async function loadCurrentStudent() {

    try {

        const response = await fetch(
            `${API_BASE_URL}/me`
        );

        if (!response.ok) {
            throw new Error(
                "Không thể lấy thông tin sinh viên."
            );
        }

        const student =
            await response.json();

        studentName.textContent =
            student.name ?? "Sinh viên";

        studentMajor.textContent =
            student.major ?? "";

        studentSemester.textContent =
            student.current_semester
                ? `Học kỳ ${student.current_semester}`
                : "";

    }
    catch (error) {

        console.error(error);

        studentName.textContent =
            "Không tải được thông tin";

        studentMajor.textContent = "";

        studentSemester.textContent = "";

        showStatus(
            "Không thể kết nối tới backend.",
            "error"
        );
    }
}


/* =========================
   SCHEDULE UI
========================= */

function getReasonText(reason) {

    if (reason === "retake") {
        return "Học lại";
    }

    if (reason === "early") {
        return "Học trước";
    }

    return "Đúng tiến độ";
}


function getReasonClass(reason) {

    if (reason === "retake") {
        return "reason-retake";
    }

    if (reason === "early") {
        return "reason-early";
    }

    return "reason-normal";
}


function parseTimeSlot(timeText) {
    const pattern = /^T(\d+)\((\d+)-(\d+)\)$/;
    const match = timeText.trim().match(pattern);

    if (!match) {
        return null;
    }

    return {
        day: parseInt(match[1], 10),
        startPeriod: parseInt(match[2], 10),
        endPeriod: parseInt(match[3], 10),
    };
}


let currentDayMobile = 2;

const DAYS_LIST = [
    { key: 2, label: "Thứ Hai", shortLabel: "T2" },
    { key: 3, label: "Thứ Ba", shortLabel: "T3" },
    { key: 4, label: "Thứ Tư", shortLabel: "T4" },
    { key: 5, label: "Thứ Năm", shortLabel: "T5" },
    { key: 6, label: "Thứ Sáu", shortLabel: "T6" },
    { key: 7, label: "Thứ Bảy", shortLabel: "T7" },
];


function getDaySummary(dayKey, schedule) {
    const dayClasses = [];
    schedule.forEach((item) => {
        if (item.times && Array.isArray(item.times)) {
            item.times.forEach((t) => {
                const slot = parseTimeSlot(t);
                if (slot && slot.day === dayKey) {
                    dayClasses.push({ ...item, slot });
                }
            });
        }
    });

    if (dayClasses.length === 0) {
        return { count: 0, text: "Hôm nay nghỉ học", hasClasses: false };
    }

    const minPeriod = Math.min(...dayClasses.map((c) => c.slot.startPeriod));
    const maxPeriod = Math.max(...dayClasses.map((c) => c.slot.endPeriod));
    return {
        count: dayClasses.length,
        text: `${dayClasses.length} môn học · Tiết ${minPeriod} - ${maxPeriod}`,
        hasClasses: true,
    };
}


function updateMobileDayView(dayNumber) {
    const grid = document.querySelector(".timetable-grid");
    if (!grid) {
        return;
    }

    grid.querySelectorAll(".active-day-col").forEach((el) => {
        el.classList.remove("active-day-col");
    });

    grid.querySelectorAll(`.day-${dayNumber}`).forEach((el) => {
        el.classList.add("active-day-col");
    });
}


function checkScreenSize() {
    const grid = document.querySelector(".timetable-grid");
    if (!grid) {
        return;
    }

    if (window.innerWidth <= 768) {
        grid.classList.add("single-day-mode");
        updateMobileDayView(currentDayMobile);
    } else {
        grid.classList.remove("single-day-mode");
        grid.querySelectorAll(".active-day-col").forEach((el) => {
            el.classList.remove("active-day-col");
        });
    }
}


function renderTimetableGrid(schedule) {
    scheduleGrid.innerHTML = "";

    // Tìm các ngày có môn học
    const daysWithClasses = new Set();
    schedule.forEach((item) => {
        if (item.times && Array.isArray(item.times)) {
            item.times.forEach((t) => {
                const slot = parseTimeSlot(t);
                if (slot) {
                    daysWithClasses.add(slot.day);
                }
            });
        }
    });

    // Nếu ngày hiện tại không có môn mà có ngày khác có môn, chọn ngày đầu tiên có môn
    if (!daysWithClasses.has(currentDayMobile) && daysWithClasses.size > 0) {
        currentDayMobile = Array.from(daysWithClasses).sort()[0];
    }

    // 1. Tạo thanh điều hướng Day Stepper trên Mobile
    const stepperWrapper = document.createElement("div");
    stepperWrapper.className = "mobile-day-stepper-wrapper";

    const stepper = document.createElement("div");
    stepper.className = "mobile-day-stepper";

    const prevBtn = document.createElement("button");
    prevBtn.className = "stepper-btn";
    prevBtn.type = "button";
    prevBtn.innerHTML = "‹";
    prevBtn.setAttribute("aria-label", "Ngày trước");

    const stepperInfo = document.createElement("div");
    stepperInfo.className = "stepper-info";

    const dayTitle = document.createElement("div");
    dayTitle.className = "stepper-day-title";

    const dayMeta = document.createElement("div");
    dayMeta.className = "stepper-day-meta";

    stepperInfo.appendChild(dayTitle);
    stepperInfo.appendChild(dayMeta);

    const nextBtn = document.createElement("button");
    nextBtn.className = "stepper-btn";
    nextBtn.type = "button";
    nextBtn.innerHTML = "›";
    nextBtn.setAttribute("aria-label", "Ngày sau");

    stepper.appendChild(prevBtn);
    stepper.appendChild(stepperInfo);
    stepper.appendChild(nextBtn);
    stepperWrapper.appendChild(stepper);

    // Dải 6 nút capsule nhanh bên dưới Stepper
    const dotsContainer = document.createElement("div");
    dotsContainer.className = "stepper-dots";

    const dotButtons = [];
    DAYS_LIST.forEach((d) => {
        const dot = document.createElement("button");
        dot.type = "button";
        const hasClasses = daysWithClasses.has(d.key);
        dot.className = `stepper-dot ${d.key === currentDayMobile ? "active" : ""}`;
        dot.innerHTML = `
            <span>${d.shortLabel}</span>
            ${hasClasses ? '<span class="stepper-dot-indicator"></span>' : ""}
        `;

        dot.addEventListener("click", () => {
            currentDayMobile = d.key;
            refreshStepperUI(d.key);
        });

        dotsContainer.appendChild(dot);
        dotButtons.push({ key: d.key, element: dot });
    });

    stepperWrapper.appendChild(dotsContainer);
    scheduleGrid.appendChild(stepperWrapper);

    function refreshStepperUI(dayKey) {
        const dayObj = DAYS_LIST.find((d) => d.key === dayKey);
        const summary = getDaySummary(dayKey, schedule);

        dayTitle.textContent = dayObj ? dayObj.label : `Thứ ${dayKey}`;
        dayMeta.textContent = summary.text;

        if (summary.hasClasses) {
            dayMeta.className = "stepper-day-meta has-classes";
        } else {
            dayMeta.className = "stepper-day-meta";
        }

        prevBtn.disabled = dayKey <= 2;
        nextBtn.disabled = dayKey >= 7;

        dotButtons.forEach((item) => {
            if (item.key === dayKey) {
                item.element.classList.add("active");
            } else {
                item.element.classList.remove("active");
            }
        });

        updateMobileDayView(dayKey);
    }

    prevBtn.addEventListener("click", () => {
        if (currentDayMobile > 2) {
            currentDayMobile--;
            refreshStepperUI(currentDayMobile);
        }
    });

    nextBtn.addEventListener("click", () => {
        if (currentDayMobile < 7) {
            currentDayMobile++;
            refreshStepperUI(currentDayMobile);
        }
    });

    // 2. Tạo Lưới Grid
    const container = document.createElement("div");
    container.className = "schedule-grid-container";

    const grid = document.createElement("div");
    grid.className = "timetable-grid";

    // Header góc trên bên trái
    const corner = document.createElement("div");
    corner.className = "timetable-header period-col";
    corner.textContent = "Tiết";
    grid.appendChild(corner);

    // Header Thứ 2 đến Thứ 7
    DAYS_LIST.forEach((d) => {
        const dayHeader = document.createElement("div");
        dayHeader.className = `timetable-header day-${d.key}`;
        dayHeader.textContent = d.label;
        grid.appendChild(dayHeader);
    });

    // 12 Tiết học và các ô nền
    for (let p = 1; p <= 12; p++) {
        const periodHeader = document.createElement("div");
        periodHeader.className = "timetable-period period-col";
        periodHeader.innerHTML = `<span>Tiết ${p}</span>`;
        grid.appendChild(periodHeader);

        for (let d = 2; d <= 7; d++) {
            const cell = document.createElement("div");
            cell.className = `timetable-cell day-${d}`;
            if (p === 5 || p === 10) {
                cell.classList.add("session-border");
            }
            cell.style.gridColumn = `${d}`;
            cell.style.gridRow = `${p + 1}`;
            grid.appendChild(cell);
        }
    }

    // 3. Đổ các môn học vào ô tương ứng
    schedule.forEach((item) => {
        if (!item.times || !Array.isArray(item.times)) {
            return;
        }

        item.times.forEach((timeStr) => {
            const slot = parseTimeSlot(timeStr);
            if (!slot || slot.day < 2 || slot.day > 7) {
                return;
            }

            const eventBlock = document.createElement("div");
            const reasonType = item.reason || "normal";
            eventBlock.className = `timetable-event day-${slot.day} ${reasonType}`;

            // Cột theo Thứ (2 -> 7)
            eventBlock.style.gridColumn = `${slot.day}`;
            // Hàng theo Tiết
            eventBlock.style.gridRow = `${slot.startPeriod + 1} / ${slot.endPeriod + 2}`;

            eventBlock.title = `${item.course_code} - ${item.course_name}\nLớp: ${item.class_id} (${item.credits} TC)\nThời gian: ${timeStr}\nTrạng thái: ${getReasonText(item.reason)}`;

            eventBlock.innerHTML = `
                <div class="timetable-event-code">${item.course_code}</div>
                <div class="timetable-event-name" title="${item.course_name}">${item.course_name}</div>
                <div class="timetable-event-meta">Lớp ${item.class_id} · T${slot.startPeriod}-${slot.endPeriod}</div>
            `;

            grid.appendChild(eventBlock);
        });
    });

    container.appendChild(grid);
    scheduleGrid.appendChild(container);

    // Cập nhật trạng thái hiển thị ban đầu của Stepper và Grid
    refreshStepperUI(currentDayMobile);
    checkScreenSize();
}


function renderSchedule(result) {

    scheduleList.innerHTML = "";

    totalCredits.textContent =
        result.total_credits;

    for (const item of result.schedule) {

        const element =
            document.createElement(
                "div"
            );

        element.className =
            "schedule-item";

        element.innerHTML = `
            <div class="course-code">
                ${item.course_code}
            </div>

            <div>

                <div class="course-name">
                    ${item.course_name}
                </div>

                <div class="course-detail">
                    ${item.credits} tín chỉ
                    · Lớp ${item.class_id}
                </div>

            </div>

            <div class="course-time">
                ${item.times.join(", ")}
            </div>

            <div>

                <span
                    class="
                        reason-badge
                        ${getReasonClass(
                            item.reason
                        )}
                    "
                >
                    ${getReasonText(
                        item.reason
                    )}
                </span>

            </div>
        `;

        scheduleList.appendChild(
            element
        );
    }

    // Render phiên bản Lưới trực quan
    renderTimetableGrid(result.schedule);

    emptyState.classList.add(
        "hidden"
    );

    scheduleContent.classList.remove(
        "hidden"
    );

    explainButton.disabled = false;
}


/* =========================
   STATUS
========================= */

function showStatus(
    message,
    type
) {

    statusBox.textContent =
        message;

    statusBox.className =
        "status-box";

    if (type === "error") {

        statusBox.classList.add(
            "status-error"
        );

    }
    else {

        statusBox.classList.add(
            "status-success"
        );
    }
}


function hideStatus() {

    statusBox.className =
        "status-box hidden";
}


/* =========================
   CREATE SCHEDULE
========================= */

async function generateSchedule() {

    const targetCredits =
        Number(
            document.getElementById(
                "target-credits"
            ).value
        );

    const allowEarly =
        document.getElementById(
            "allow-early"
        ).checked;


    if (
        targetCredits < 15
        ||
        targetCredits > 25
    ) {

        showStatus(
            "Số tín chỉ phải từ 15 đến 25.",
            "error"
        );

        return;
    }


    hideStatus();

    aiExplanation.classList.add(
        "hidden"
    );

    currentSchedule = null;

    explainButton.disabled = true;


    const oldText =
        generateButton.textContent;

    generateButton.disabled = true;

    generateButton.textContent =
        "Đang tạo lịch...";


    try {

        const response = await fetch(
            `${API_BASE_URL}/schedule`,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    target_credits:
                        targetCredits,

                    allow_early:
                        allowEarly
                })
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            console.error(data);

            throw new Error(
                "Yêu cầu tạo lịch không hợp lệ."
            );
        }


        if (!data.success) {

            showStatus(
                data.message
                ??
                "Không tìm được thời khóa biểu phù hợp.",
                "error"
            );

            return;
        }


        currentSchedule = data;

        renderSchedule(data);

        showStatus(
            "Đã tạo thời khóa biểu thành công.",
            "success"
        );

    }
    catch (error) {

        console.error(error);

        showStatus(
            "Không thể tạo thời khóa biểu. "
            +
            "Hãy kiểm tra backend.",
            "error"
        );

    }
    finally {

        generateButton.disabled = false;

        generateButton.textContent =
            oldText;
    }
}


/* =========================
   AI EXPLANATION
========================= */

async function explainSchedule() {

    if (!currentSchedule) {

        showStatus(
            "Bạn cần tạo thời khóa biểu trước.",
            "error"
        );

        return;
    }


    const oldText =
        explainButton.textContent;

    explainButton.disabled = true;

    explainButton.textContent =
        "AI đang giải thích...";

    aiExplanation.classList.add(
        "hidden"
    );


    try {

        const response = await fetch(
            `${API_BASE_URL}/schedule/explain`,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    schedule_result:
                        currentSchedule
                })
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            console.error(data);

            throw new Error(
                "AI không thể tạo giải thích."
            );
        }

        aiExplanation.innerHTML = marked.parse(data.explanation);

        aiExplanation.classList.remove(
            "hidden"
        );

    }
    catch (error) {

        console.error(error);

        showStatus(
            "Không thể tạo giải thích AI lúc này.",
            "error"
        );

    }
    finally {

        explainButton.disabled = false;

        explainButton.textContent =
            oldText;
    }
}


/* =========================
   EVENTS
========================= */

tabListView.addEventListener("click", () => {
    tabListView.classList.add("active");
    tabGridView.classList.remove("active");
    scheduleList.classList.remove("hidden");
    scheduleGrid.classList.add("hidden");
});

tabGridView.addEventListener("click", () => {
    tabGridView.classList.add("active");
    tabListView.classList.remove("active");
    scheduleGrid.classList.remove("hidden");
    scheduleList.classList.add("hidden");
});

generateButton.addEventListener(
    "click",
    generateSchedule
);


explainButton.addEventListener(
    "click",
    explainSchedule
);


document.addEventListener(
    "DOMContentLoaded",
    () => {

        explainButton.disabled = true;

        loadCurrentStudent();
    }
);