const tg = window.Telegram.WebApp;
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file");
const uploadBtn = document.getElementById("upload");
const statusDiv = document.getElementById("status");

// Telegram MainButton
tg.MainButton.setText("Upload");
tg.MainButton.show();

let selectedFile = null;

// --- Drag & Drop ---
dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("hover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("hover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("hover");
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".ipa")) {
        selectedFile = file;
        statusDiv.innerText = `📂 Selected: ${file.name}`;
    } else {
        statusDiv.innerText = "❌ Only .ipa files are allowed";
    }
});

dropZone.addEventListener("click", () => {
    fileInput.click();
});

fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file && file.name.endsWith(".ipa")) {
        selectedFile = file;
        statusDiv.innerText = `📂 Selected: ${file.name}`;
    } else {
        statusDiv.innerText = "❌ Only .ipa files are allowed";
    }
});

// --- Upload ---
uploadBtn.addEventListener("click", async () => {
    if (!selectedFile) {
        statusDiv.innerText = "❌ Please select a file first";
        return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload", true);

    xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            statusDiv.innerText = `🔄 Uploading: ${percent}%`;
        }
    };

    xhr.onload = () => {
        if (xhr.status === 200) {
            const resp = JSON.parse(xhr.responseText);
            statusDiv.innerText = `✅ Uploaded: ${resp.saved}`;
            tg.MainButton.setText("Done!");
        } else {
            statusDiv.innerText = `❌ Upload error: ${xhr.status}`;
        }
    };

    xhr.onerror = () => {
        statusDiv.innerText = "❌ Network error during upload";
    };

    xhr.send(formData);
});