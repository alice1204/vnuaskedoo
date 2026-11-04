const API_BASE_URL =
    (window.location.port === "5500" || window.location.protocol === "file:")
        ? "http://127.0.0.1:8000"
        : window.location.origin;

const mathRule = /^(?:\$\$([\s\S]+?)\$\$|\$([^\s$](?:[\s\S]*?[^\s$])?)\$)/;
const customKatexExtension = {
    name: 'math',
    level: 'inline',
    start(src) { return src.indexOf('$'); },
    tokenizer(src, tokens) {
        const match = src.match(mathRule);
        if (match) {
            const isBlock = !!match[1];
            const text = isBlock ? match[1] : match[2];
            return {
                type: 'math',
                raw: match[0],
                text: text,
                displayMode: isBlock
            };
        }
    },
    renderer(token) {
        if (window.katex) {
            try {
                return katex.renderToString(token.text, { displayMode: token.displayMode, throwOnError: false });
            } catch (e) {
                return token.raw;
            }
        }
        return token.raw;
    }
};

if (window.marked) {
    marked.use({ extensions: [customKatexExtension] });
}



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
        "AI đang viết nhận xét...";

    aiExplanation.classList.remove(
        "hidden"
    );
    aiExplanation.innerHTML = "<p><em>AI đang kết nối và viết nhận xét...</em></p>";


    try {

        const response = await fetch(
            `${API_BASE_URL}/schedule/explain-stream`,
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


        if (!response.ok) {
            throw new Error(
                "AI không thể tạo giải thích."
            );
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let accumulatedText = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }

            const chunk = decoder.decode(value, { stream: true });
            accumulatedText += chunk;
            aiExplanation.innerHTML = marked.parse(accumulatedText);
        }

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
   EVENTS & TAB SWITCHING
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

// MAIN NAVIGATION TABS (3 TABS)
const tabNavChat = document.getElementById("tab-nav-chat");
const tabNavScheduler = document.getElementById("tab-nav-scheduler");
const tabNavTeacher = document.getElementById("tab-nav-teacher");

const viewChat = document.getElementById("view-chat");
const viewScheduler = document.getElementById("view-scheduler");
const viewTeacher = document.getElementById("view-teacher");

const allTabBtns = [tabNavChat, tabNavScheduler, tabNavTeacher];
const allViews = [viewChat, viewScheduler, viewTeacher];

function switchMainTab(targetBtn, targetView) {
    allTabBtns.forEach(b => b && b.classList.remove("active"));
    allViews.forEach(v => v && v.classList.add("hidden"));

    if (targetBtn) targetBtn.classList.add("active");
    if (targetView) targetView.classList.remove("hidden");
}

tabNavChat.addEventListener("click", () => {
    switchMainTab(tabNavChat, viewChat);
});

tabNavScheduler.addEventListener("click", () => {
    switchMainTab(tabNavScheduler, viewScheduler);
});

if (tabNavTeacher) {
    tabNavTeacher.addEventListener("click", () => {
        switchMainTab(tabNavTeacher, viewTeacher);
        loadTeacherClasses();
    });
}



/* =========================================================
   CHATBOT CONTROLLER (STEP 4 AGENT HARNESS)
========================================================= */

const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatSendBtn = document.getElementById("chat-send-btn");
const chatMessages = document.getElementById("chat-messages");

let chatSessionId = sessionStorage.getItem("chat_session_id");
if (!chatSessionId) {
    chatSessionId = "session_" + Math.random().toString(36).substring(2, 10);
    sessionStorage.setItem("chat_session_id", chatSessionId);
}

function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user-row";
    row.innerHTML = `
        <div class="avatar">👤</div>
        <div class="message-bubble user-bubble">${text}</div>
    `;
    chatMessages.appendChild(row);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendBotPlaceholder() {
    const row = document.createElement("div");
    row.className = "message-row bot-row";
    row.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="message-bubble bot-bubble">
            <span class="loading-dots">Đang tra cứu dữ liệu...</span>
        </div>
    `;
    chatMessages.appendChild(row);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return row.querySelector(".message-bubble");
}

async function sendChatMessage(message) {
    if (!message || !message.trim()) return;

    appendUserMessage(message);
    chatInput.value = "";
    chatInput.disabled = true;
    chatSendBtn.disabled = true;

    const botBubble = appendBotPlaceholder();
    let accumulatedText = "";

    try {
        const response = await fetch(`${API_BASE_URL}/chat/stream`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                session_id: chatSessionId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: Lỗi máy chủ`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        botBubble.innerHTML = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            accumulatedText += chunk;
            if (window.marked) {
                botBubble.innerHTML = marked.parse(accumulatedText);
            } else {
                botBubble.innerText = accumulatedText;
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

    } catch (err) {
        console.error("Chat error:", err);
        botBubble.innerHTML = `<p style="color: #ef4444;">⚠️ Không thể kết nối tới Trợ lý AI: ${err.message}. Vui lòng thử lại.</p>`;
    } finally {
        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        chatInput.focus();
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (query) {
        sendChatMessage(query);
    }
});

// Quick prompts chips
document.querySelectorAll(".chip-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        const query = btn.getAttribute("data-query");
        if (query) {
            sendChatMessage(query);
        }
    });
});

// ==========================================
// DARK / LIGHT MODE CONTROLLER
// ==========================================
function initThemeToggle() {
    const themeToggleBtn = document.getElementById("theme-toggle");
    if (!themeToggleBtn) return;

    function applyTheme(isDark) {
        if (isDark) {
            document.documentElement.classList.add("dark-mode");
            document.body.classList.add("dark-mode");
            themeToggleBtn.setAttribute("aria-label", "Chuyển sang giao diện Sáng");
            themeToggleBtn.setAttribute("title", "Chuyển sang giao diện Sáng");
        } else {
            document.documentElement.classList.remove("dark-mode");
            document.body.classList.remove("dark-mode");
            themeToggleBtn.setAttribute("aria-label", "Chuyển sang giao diện Tối");
            themeToggleBtn.setAttribute("title", "Chuyển sang giao diện Tối");
        }
    }

    // 1. Initial State check
    const savedTheme = localStorage.getItem("theme");
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const isDark = savedTheme ? savedTheme === "dark" : prefersDark;
    applyTheme(isDark);

    // 2. Click Handler
    themeToggleBtn.addEventListener("click", () => {
        const currentlyDark = document.body.classList.contains("dark-mode");
        const nextDark = !currentlyDark;
        applyTheme(nextDark);
        localStorage.setItem("theme", nextDark ? "dark" : "light");
    });

    // 3. Listen for OS theme changes if user hasn't explicitly set a preference
    if (window.matchMedia) {
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
            if (!localStorage.getItem("theme")) {
                applyTheme(e.matches);
            }
        });
    }
}

document.addEventListener(
    "DOMContentLoaded",
    () => {
        initThemeToggle();
        explainButton.disabled = true;
        loadCurrentStudent();
        initTeacherEventListeners();
    }
);

/* ==========================================================================
   HELPER & TEACHER GRADEBOOK CONTROLLER
   ========================================================================== */

function getGradeBadgeHtml(letter) {
    if (!letter) return '<span class="text-muted">--</span>';
    const clean = letter.toLowerCase().replace("+", "-plus");
    return `<span class="grade-badge ${clean}">${letter}</span>`;
}


let cachedTeacherClasses = [];

async function loadTeacherClasses() {
    const classSelect = document.getElementById("teacher-class-select");
    try {
        const response = await fetch(`${API_BASE_URL}/api/teacher/classes`);
        if (!response.ok) throw new Error("Không thể tải danh sách lớp học phần của giảng viên.");

        const data = await response.json();
        cachedTeacherClasses = data.classes || [];

        if (cachedTeacherClasses.length === 0) {
            classSelect.innerHTML = `<option value="">Giảng viên chưa được phân công lớp nào.</option>`;
            return;
        }

        classSelect.innerHTML = cachedTeacherClasses.map(c => `
            <option value="${c.class_code}">${c.class_code} - ${c.course_name} (Học kỳ: ${c.semester})</option>
        `).join("");

        // Tự động nạp lớp đầu tiên
        const firstClass = cachedTeacherClasses[0];
        loadClassGradebook(firstClass.class_code);

    } catch (error) {
        console.error("Lỗi khi tải lớp giảng viên:", error);
        classSelect.innerHTML = `<option value="">Lỗi: ${error.message}</option>`;
    }
}

async function loadClassGradebook(classCode) {
    if (!classCode) return;

    const classMeta = document.getElementById("teacher-class-meta");
    const statsGrid = document.getElementById("teacher-stats-grid");
    const distChart = document.getElementById("teacher-distribution-chart");
    const riskList = document.getElementById("teacher-risk-list");
    const tbody = document.getElementById("gradebook-tbody");

    // Tìm thông tin lớp trong cache
    const currentCls = cachedTeacherClasses.find(c => c.class_code === classCode);
    if (currentCls) {
        classMeta.innerHTML = `
            <span>📍 Phòng: <strong>${currentCls.room || 'ND201'}</strong></span>
            <span>⏰ Lịch: <strong>${currentCls.schedule || 'T2(1-3)'}</strong></span>
            <span>📚 Số TC: <strong>${currentCls.credits} TC</strong></span>
        `;
    }

    try {
        tbody.innerHTML = `<tr><td colspan="9" class="text-center">Đang tải danh sách điểm lớp ${classCode}...</td></tr>`;

        const [gradesRes, statsRes] = await Promise.all([
            fetch(`${API_BASE_URL}/api/teacher/classes/${classCode}/grades`),
            fetch(`${API_BASE_URL}/api/teacher/classes/${classCode}/stats`)
        ]);

        if (!gradesRes.ok) throw new Error("Không thể tải danh sách điểm của lớp.");

        const gradesData = await gradesRes.json();
        const statsData = statsRes.ok ? await statsRes.json() : null;

        // 1. Cập nhật thống kê nhanh
        statsGrid.classList.remove("hidden");
        document.getElementById("t-stat-total").textContent = statsData?.total_students ?? gradesData.total_students;
        document.getElementById("t-stat-avg").textContent = statsData?.average_score_10 ? `${statsData.average_score_10}/10` : 'Đang học';
        document.getElementById("t-stat-pass-rate").textContent = statsData?.pass_rate_percentage !== undefined ? `${statsData.pass_rate_percentage}%` : '--';
        document.getElementById("t-stat-risk").textContent = statsData?.at_risk_students ? statsData.at_risk_students.length : 0;

        // 2. Render Biểu đồ phổ điểm chữ
        if (statsData && statsData.letter_distribution) {
            distChart.innerHTML = statsData.letter_distribution.map(item => {
                let barClass = 'bar-c';
                if (item.letter === 'A') barClass = 'bar-a';
                else if (item.letter === 'B+' || item.letter === 'B') barClass = 'bar-b';
                else if (item.letter === 'F') barClass = 'bar-f';

                return `
                    <div class="chart-bar-row">
                        <span class="chart-bar-label">${item.letter}</span>
                        <div class="chart-bar-track">
                            <div class="chart-bar-fill ${barClass}" style="width: ${item.percentage}%;"></div>
                        </div>
                        <span class="chart-bar-count">${item.count} SV (${item.percentage}%)</span>
                    </div>
                `;
            }).join("");
        } else {
            distChart.innerHTML = `<p class="text-muted">Chưa có dữ liệu phổ điểm.</p>`;
        }

        // 3. Render Danh sách sinh viên nguy cơ
        if (statsData && statsData.at_risk_students && statsData.at_risk_students.length > 0) {
            riskList.innerHTML = statsData.at_risk_students.map(r => `
                <div class="risk-item">
                    <div>
                        <strong>${r.student_name} (${r.student_id})</strong>
                        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 2px;">
                            ${r.reason}
                        </div>
                    </div>
                    <span class="grade-badge f">Cảnh báo</span>
                </div>
            `).join("");
        } else {
            riskList.innerHTML = `<p class="text-muted" style="color: #10b981;">🎉 Toàn bộ sinh viên trong lớp đều có điểm thành phần an toàn!</p>`;
        }

        // 4. Render Bảng danh sách điểm (chỉ xem, không sửa điểm)
        const records = gradesData.grades || [];
        if (records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">Lớp học phần hiện chưa có sinh viên đăng ký.</td></tr>`;
            return;
        }

        tbody.innerHTML = records.map((r, index) => {
            const comps = r.components || {};
            const tp1Score = comps.tp1?.score !== null && comps.tp1?.score !== undefined ? comps.tp1.score : null;
            const tp2Score = comps.tp2?.score !== null && comps.tp2?.score !== undefined ? comps.tp2.score : null;
            const tp3Score = comps.tp3?.score !== null && comps.tp3?.score !== undefined ? comps.tp3.score : null;

            return `
                <tr>
                    <td class="text-center">${index + 1}</td>
                    <td><strong>${r.student_id}</strong></td>
                    <td>${r.student_name || '--'}</td>
                    <td><small>${r.cohort || ''} ${r.major || ''}</small></td>
                    <td class="text-center"><strong>${tp1Score !== null ? tp1Score : '<span class="text-muted">--</span>'}</strong></td>
                    <td class="text-center"><strong>${tp2Score !== null ? tp2Score : '<span class="text-muted">--</span>'}</strong></td>
                    <td class="text-center"><strong>${tp3Score !== null ? tp3Score : '<span class="text-muted">--</span>'}</strong></td>
                    <td class="text-center"><strong>${r.total_score_10 !== null ? r.total_score_10 : '--'}</strong></td>
                    <td class="text-center">${getGradeBadgeHtml(r.letter_grade)}</td>
                </tr>
            `;
        }).join("");

    } catch (error) {
        console.error("Lỗi khi tải danh sách điểm:", error);
        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted" style="color: #ef4444;">Không thể nạp dữ liệu: ${error.message}</td></tr>`;
    }
}

function initTeacherEventListeners() {
    // Chọn lớp học phần giảng viên
    const classSelect = document.getElementById("teacher-class-select");
    if (classSelect) {
        classSelect.addEventListener("change", (e) => {
            loadClassGradebook(e.target.value);
        });
    }

    // Nút làm mới sổ điểm
    const refreshBtn = document.getElementById("refresh-gradebook-btn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            const classCode = document.getElementById("teacher-class-select").value;
            if (classCode) loadClassGradebook(classCode);
        });
    }
}

