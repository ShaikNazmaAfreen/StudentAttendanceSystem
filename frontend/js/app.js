// ==========================================
// 1. BACKEND API URL AND APPLICATION STATE
// ==========================================

const API_URL = "http://127.0.0.1:5000/api";

let allStudents = [];
let isAuthenticated = false;
let cameraStream = null;


// ==========================================
// 2. HELPER FUNCTIONS
// ==========================================

function escapeHTML(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function(character) {
        return {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        }[character];
    });
}

function statusBadge(status) {
    if (status === "Present") {
        return '<span class="status-badge status-present">Present</span>';
    }

    if (status === "Absent") {
        return '<span class="status-badge status-absent">Absent</span>';
    }

    return '<span class="status-badge status-pending">Pending</span>';
}

function getToday() {
    const now = new Date();

    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");

    return year + "-" + month + "-" + day;
}


// ==========================================
// 3. LOGIN AND SESSION MANAGEMENT
// ==========================================

function showLogin(message, messageType) {

    stopCamera();

    isAuthenticated = false;
    allStudents = [];

    document.getElementById("protected-app").style.display = "none";
    document.getElementById("login-page").style.display = "flex";

    const loginMessage = document.getElementById("login-message");

    loginMessage.textContent = message || "";
    loginMessage.className = "login-message";

    if (messageType) {
        loginMessage.classList.add(messageType);
    }

    document.getElementById("login-password").value = "";
}

function showApplication() {

    isAuthenticated = true;

    document.getElementById("login-page").style.display = "none";
    document.getElementById("protected-app").style.display = "flex";

    document.getElementById("login-message").textContent = "";

    navigateTo("dashboard");
}


// Check whether an administrator session already exists.
async function checkSession() {

    try {

        const response = await fetch(API_URL + "/session", {
            method: "GET",
            credentials: "include"
        });

        const data = await response.json();

        if (response.ok && data.logged_in) {
            showApplication();
        } else {
            showLogin("", "");
        }

    } catch (error) {

        showLogin(
            "Unable to connect to the server. Please start the backend.",
            "error"
        );
    }
}


// Administrator login.
async function loginAdmin(event) {

    event.preventDefault();

    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;

    const loginButton = document.getElementById("login-button");

    const loginMessage = document.getElementById("login-message");

    loginButton.disabled = true;
    loginButton.textContent = "Signing in...";

    loginMessage.textContent = "";
    loginMessage.className = "login-message";

    try {

        const response = await fetch(API_URL + "/login", {

            method: "POST",

            credentials: "include",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Login failed.");
        }

        loginMessage.textContent = "Login successful!";
        loginMessage.className = "login-message success";

        showApplication();

    } catch (error) {

        loginMessage.textContent = error.message;
        loginMessage.className = "login-message error";

    } finally {

        loginButton.disabled = false;
        loginButton.textContent = "Login";
    }
}


// Administrator logout.
async function logoutAdmin() {

    stopCamera();

    try {

        await fetch(API_URL + "/logout", {
            method: "POST",
            credentials: "include"
        });

    } catch (error) {

        console.error("Logout request failed:", error);
    }

    showLogin("You have been logged out successfully.", "success");
}


// ==========================================
// 4. AUTHENTICATED API REQUEST HELPER
// ==========================================

// All protected API requests must use this function.
// It automatically includes the administrator session cookie.

async function apiFetch(url, options = {}) {

    if (!isAuthenticated) {
        throw new Error("Please log in as administrator.");
    }

    const response = await fetch(url, {
        ...options,
        credentials: "include"
    });

    // Only an actual 401 response triggers administrator logout.
    // Unknown-person recognition now returns HTTP 200 from Flask.
    if (response.status === 401) {

        showLogin(
            "Your session has expired. Please log in again.",
            "error"
        );

        throw new Error("Administrator session expired.");
    }

    return response;
}


// ==========================================
// 5. PAGE NAVIGATION
// ==========================================

function navigateTo(pageName) {

    if (!isAuthenticated) {
        return;
    }

    document.querySelectorAll(".page").forEach(function(page) {
        page.classList.remove("active");
    });

    document.querySelectorAll(".nav-link").forEach(function(button) {
        button.classList.remove("active");
    });

    const selectedPage = document.getElementById(pageName);

    if (!selectedPage) return;

    selectedPage.classList.add("active");

    const selectedButton = document.querySelector(
        '.nav-link[data-page="' + pageName + '"]'
    );

    if (selectedButton) {
        selectedButton.classList.add("active");
    }

    const titles = {
        dashboard: [
            "Dashboard Overview",
            "Welcome to your student attendance management system."
        ],
        attendance: [
            "Mark Attendance",
            "Identify students using face recognition."
        ],
        students: [
            "Student Management",
            "View your registered students."
        ],
        reports: [
            "Attendance Reports",
            "View date-wise attendance records."
        ]
    };

    document.getElementById("page-title").textContent = titles[pageName][0];
    document.getElementById("page-subtitle").textContent = titles[pageName][1];

    if (pageName === "dashboard") loadDashboard();
    if (pageName === "students") loadStudents();
    if (pageName === "reports") loadReport();

    if (pageName !== "attendance" && cameraStream) {
        stopCamera();
    }
}


// ==========================================
// 6. LOAD REGISTERED STUDENTS
// ==========================================

async function loadStudents() {

    const table = document.getElementById("students-table");

    table.innerHTML = '<tr><td colspan="4">Loading students...</td></tr>';

    try {

        const response = await apiFetch(API_URL + "/students");

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Student loading failed.");
        }

        allStudents = data.students;

        document.getElementById("student-total").textContent =
            allStudents.length + " Students";

        renderStudents(allStudents);

    } catch (error) {

        table.innerHTML =
            '<tr><td colspan="4">' + escapeHTML(error.message) + '</td></tr>';
    }
}


// ==========================================
// 7. DISPLAY STUDENTS
// ==========================================

function renderStudents(students) {

    const table = document.getElementById("students-table");

    if (students.length === 0) {
        table.innerHTML = '<tr><td colspan="4">No students found.</td></tr>';
        return;
    }

    table.innerHTML = students.map(function(student) {

        return '<tr>' +
            '<td>' + escapeHTML(student.student_id) + '</td>' +
            '<td>' + escapeHTML(student.full_name) + '</td>' +
            '<td>' + escapeHTML(student.department) + '</td>' +
            '<td>' + escapeHTML(student.year) + '</td>' +
            '</tr>';

    }).join("");
}


// ==========================================
// 8. STUDENT SEARCH
// ==========================================

function searchStudents() {

    const searchInput = document.getElementById("student-search");
    const searchText = searchInput.value.toLowerCase().trim();

    const filteredStudents = allStudents.filter(function(student) {

        const studentID = String(student.student_id).toLowerCase();
        const studentName = String(student.full_name).toLowerCase();

        return studentID.includes(searchText) ||
               studentName.includes(searchText);
    });

    renderStudents(filteredStudents);
}


// ==========================================
// 9. LOAD DASHBOARD
// ==========================================

async function loadDashboard() {

    if (!isAuthenticated) return;

    try {

        const results = await Promise.all([

            apiFetch(API_URL + "/students"),

            apiFetch(API_URL + "/attendance?date=" + getToday())

        ]);

        const studentResponse = results[0];
        const attendanceResponse = results[1];

        const studentData = await studentResponse.json();
        const attendanceData = await attendanceResponse.json();

        if (!studentData.success || !attendanceData.success) {
            throw new Error("Backend returned an unsuccessful response.");
        }

        const totalStudents = studentData.students.length;
        const records = attendanceData.attendance;

        const present = records.filter(function(record) {
            return record.status === "Present";
        });

        const absent = records.filter(function(record) {
            return record.status === "Absent";
        });

        const pending = totalStudents - present.length - absent.length;

        document.getElementById("total-students").textContent = totalStudents;
        document.getElementById("present-count").textContent = present.length;
        document.getElementById("absent-count").textContent = absent.length;
        document.getElementById("pending-count").textContent = pending;

        renderTodayAttendance(records);

    } catch (error) {

        if (isAuthenticated) {
            document.getElementById("today-table").innerHTML =
                '<tr><td colspan="5">' + escapeHTML(error.message) + '</td></tr>';
        }
    }
}


// ==========================================
// 10. DISPLAY TODAY'S ATTENDANCE
// ==========================================

function renderTodayAttendance(records) {

    const table = document.getElementById("today-table");

    if (records.length === 0) {
        table.innerHTML =
            '<tr><td colspan="5">No registered students found.</td></tr>';
        return;
    }

    table.innerHTML = records.map(function(record) {

        return '<tr>' +
            '<td>' + escapeHTML(record.student_id) + '</td>' +
            '<td>' + escapeHTML(record.full_name) + '</td>' +
            '<td>' + escapeHTML(record.department) + '</td>' +
            '<td>' + escapeHTML(record.attendance_time || "--") + '</td>' +
            '<td>' + statusBadge(record.status) + '</td>' +
            '</tr>';

    }).join("");
}


// ==========================================
// 11. LOAD ATTENDANCE REPORT
// ==========================================

async function loadReport() {

    if (!isAuthenticated) return;

    const selectedDate =
        document.getElementById("report-date").value || getToday();

    const table = document.getElementById("report-table");

    table.innerHTML = '<tr><td colspan="5">Loading report...</td></tr>';

    try {

        const response = await apiFetch(
            API_URL + "/attendance?date=" + encodeURIComponent(selectedDate)
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Report loading failed.");
        }

        const records = data.attendance;

        const present = records.filter(function(record) {
            return record.status === "Present";
        }).length;

        const absent = records.filter(function(record) {
            return record.status === "Absent";
        }).length;

        const pending = records.length - present - absent;

        document.getElementById("report-present").textContent = present;
        document.getElementById("report-absent").textContent = absent;
        document.getElementById("report-pending").textContent = pending;

        if (records.length === 0) {
            table.innerHTML =
                '<tr><td colspan="5">No student records found.</td></tr>';
            return;
        }

        table.innerHTML = records.map(function(record) {

            return '<tr>' +
                '<td>' + escapeHTML(record.student_id) + '</td>' +
                '<td>' + escapeHTML(record.full_name) + '</td>' +
                '<td>' + escapeHTML(record.department) + '</td>' +
                '<td>' + escapeHTML(record.attendance_time || "--") + '</td>' +
                '<td>' + statusBadge(record.status) + '</td>' +
                '</tr>';

        }).join("");

    } catch (error) {

        if (isAuthenticated) {
            table.innerHTML =
                '<tr><td colspan="5">' + escapeHTML(error.message) + '</td></tr>';
        }
    }
}


// ==========================================
// 12. LIVE CAMERA ELEMENTS
// ==========================================

const cameraVideo = document.getElementById("camera");
const cameraPlaceholder = document.getElementById("camera-placeholder");

const startCameraButton = document.getElementById("start-camera");
const captureFaceButton = document.getElementById("capture-face");
const stopCameraButton = document.getElementById("stop-camera");

const captureCanvas = document.getElementById("capture-canvas");
const recognitionResult = document.getElementById("recognition-result");


// Display recognition messages.
function showRecognitionMessage(message, type) {

    recognitionResult.textContent = message;
    recognitionResult.className = "result-message " + type;
}


// ==========================================
// 13. START WEBCAM
// ==========================================

async function startCamera() {

    if (!isAuthenticated) return;

    try {

        if (!navigator.mediaDevices ||
            !navigator.mediaDevices.getUserMedia) {

            throw new Error(
                "Camera access is unavailable. Please use localhost in Chrome or Edge."
            );
        }

        cameraStream = await navigator.mediaDevices.getUserMedia({

            video: {
                facingMode: "user",
                width: { ideal: 640 },
                height: { ideal: 480 }
            },

            audio: false
        });

        cameraVideo.srcObject = cameraStream;

        await cameraVideo.play();

        cameraPlaceholder.style.display = "none";
        cameraVideo.style.display = "block";

        startCameraButton.disabled = true;
        captureFaceButton.disabled = false;
        stopCameraButton.disabled = false;

        showRecognitionMessage(
            "Camera started. Position your face clearly in the frame.",
            "info"
        );

    } catch (error) {

        showRecognitionMessage(
            "Camera error: " + error.message,
            "error"
        );
    }
}


// ==========================================
// 14. CAPTURE AND RECOGNIZE FACE
// ==========================================

async function captureAndRecognize() {

    if (!isAuthenticated) return;

    if (!cameraStream) {
        showRecognitionMessage("Please start the camera first.", "error");
        return;
    }

    if (cameraVideo.videoWidth === 0 ||
        cameraVideo.videoHeight === 0) {

        showRecognitionMessage(
            "Camera is not ready. Please wait and try again.",
            "error"
        );
        return;
    }

    captureFaceButton.disabled = true;

    showRecognitionMessage(
        "Processing your face. Please wait...",
        "info"
    );

    try {

        captureCanvas.width = cameraVideo.videoWidth;
        captureCanvas.height = cameraVideo.videoHeight;

        const context = captureCanvas.getContext("2d");

        context.drawImage(
            cameraVideo,
            0,
            0,
            captureCanvas.width,
            captureCanvas.height
        );

        const imageData = captureCanvas.toDataURL("image/jpeg", 0.85);

        const response = await apiFetch(API_URL + "/recognize", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                image: imageData
            })
        });

        const data = await response.json();

        if (data.success) {

            const student = data.student;

            showRecognitionMessage(
                "Attendance marked successfully!\n" +
                "Name: " + student.name + "\n" +
                "Student ID: " + student.student_id + "\n" +
                "Department: " + student.department + "\n" +
                "Similarity: " + student.similarity,
                "success"
            );

            loadDashboard();

            if (document.getElementById("reports").classList.contains("active")) {
                loadReport();
            }

        } else {

            // An unknown person is displayed as a recognition result.
            // It does not log out the administrator.
            let message = data.message || "Face recognition failed.";

            if (data.student) {

                message += "\n\nDetected Student: " + data.student.name;
                message += "\nStudent ID: " + data.student.student_id;
                message += "\nDepartment: " + data.student.department;
                message += "\nSimilarity: " + data.student.similarity;

            }

            message += "\nHTTP Status: " + response.status;

            showRecognitionMessage(message, "error");
        }

    } catch (error) {

        showRecognitionMessage(
            "Could not connect to the recognition server: " + error.message,
            "error"
        );

    } finally {

        if (isAuthenticated && cameraStream) {
            captureFaceButton.disabled = false;
        }
    }
}


// ==========================================
// 15. STOP WEBCAM
// ==========================================

function stopCamera() {

    if (cameraStream) {

        cameraStream.getTracks().forEach(function(track) {
            track.stop();
        });

        cameraStream = null;
    }

    if (!cameraVideo) return;

    cameraVideo.srcObject = null;

    cameraVideo.style.display = "none";
    cameraPlaceholder.style.display = "flex";

    startCameraButton.disabled = false;
    captureFaceButton.disabled = true;
    stopCameraButton.disabled = true;

    if (recognitionResult) {
        showRecognitionMessage("Camera stopped.", "info");
    }
}


// ==========================================
// 16. INITIALIZE EVENT LISTENERS
// ==========================================

document.addEventListener("DOMContentLoaded", function() {

    document.getElementById("report-date").value = getToday();

    // Login form.
    document.getElementById("login-form").addEventListener(
        "submit",
        loginAdmin
    );

    // Logout button.
    document.getElementById("logout-button").addEventListener(
        "click",
        logoutAdmin
    );

    // Navigation.
    document.querySelectorAll(".nav-link").forEach(function(button) {

        button.addEventListener("click", function() {
            navigateTo(button.dataset.page);
        });

    });

    // Dashboard shortcut.
    document.querySelectorAll("[data-go]").forEach(function(button) {

        button.addEventListener("click", function() {
            navigateTo(button.dataset.go);
        });

    });

    // Student search.
    document.getElementById("student-search").addEventListener(
        "input",
        searchStudents
    );

    // Reports.
    document.getElementById("load-report").addEventListener(
        "click",
        loadReport
    );

    // Camera buttons.
    startCameraButton.addEventListener("click", startCamera);

    captureFaceButton.addEventListener("click", captureAndRecognize);

    stopCameraButton.addEventListener("click", stopCamera);

    // Check administrator session when the page opens.
    checkSession();
});


// Stop camera when browser closes or refreshes.
window.addEventListener("beforeunload", stopCamera);