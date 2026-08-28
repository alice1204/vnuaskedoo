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


function renderTimetableGrid(schedule) {
    scheduleGrid.innerHTML = "";

    const container = document.createElement("div");
    container.className = "schedule-grid-container";

    const grid = document.createElement("div");
    grid.className = "timetable-grid";

    // Header: Góc trên bên trái + Thứ 2 đến Thứ 7
    const corner = document.createElement("div");
    corner.className = "timetable-header";
    corner.textContent = "Tiết / Thứ";
    grid.appendChild(corner);

    const days = [
        { key: 2, label: "Thứ 2" },
        { key: 3, label: "Thứ 3" },
        { key: 4, label: "Thứ 4" },
        { key: 5, label: "Thứ 5" },
        { key: 6, label: "Thứ 6" },
        { key: 7, label: "Thứ 7" },
    ];

    days.forEach((d) => {
        const dayHeader = document.createElement("div");
        dayHeader.className = "timetable-header";
        dayHeader.textContent = d.label;
        grid.appendChild(dayHeader);
    });

    // 12 Tiết học và các ô nền
    for (let p = 1; p <= 12; p++) {
        const periodHeader = document.createElement("div");
        periodHeader.className = "timetable-period";
        periodHeader.innerHTML = `<span>Tiết ${p}</span>`;
        grid.appendChild(periodHeader);

        for (let d = 2; d <= 7; d++) {
            const cell = document.createElement("div");
            cell.className = "timetable-cell";
            if (p === 5 || p === 10) {
                cell.classList.add("session-border");
            }
            cell.style.gridColumn = `${d}`;
            cell.style.gridRow = `${p + 1}`;
            grid.appendChild(cell);
        }
    }

    // Đổ các môn học vào ô tương ứng
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
            eventBlock.className = `timetable-event ${reasonType}`;

            // Cột theo Thứ (2 -> 7)
            eventBlock.style.gridColumn = `${slot.day}`;
            // Hàng theo Tiết (Tiết 1 -> row 2, kết thúc ở tiết endPeriod + 1)
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