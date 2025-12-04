const tg = window.Telegram.WebApp;

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file");
const uploadBtn = document.getElementById("upload");
const statusDiv = document.getElementById("status");

const progressContainer = document.getElementById("progress-container");
const progressBar = document.getElementById("progress-bar");
const speedInfo = document.getElementById("speed-info");

tg.MainButton.setText("Upload");
tg.MainButton.show();

let selectedFile = null;

// === Drag & Drop ===
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
    handleFile(file);
});

dropZone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    handleFile(file);
});

function handleFile(file) {
    if (file && file.name.endsWith(".ipa")) {
        selectedFile = file;
        statusDiv.innerText = `📂 Selected: ${file.name}`;
    } else {
        statusDiv.innerText = "❌ Only .ipa files are allowed";
    }
}

// === Upload ===
uploadBtn.addEventListener("click", async () => {
    if (!selectedFile) {
        statusDiv.innerText = "❌ Please select a file first";
        return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload", true);

    let lastLoaded = 0;
    let lastTime = Date.now();

    progressContainer.style.display = "block";
    speedInfo.style.display = "block";

    progressBar.style.width = "0%";
    speedInfo.innerText = "";

    xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            progressBar.style.width = percent + "%";
            statusDiv.innerText = `🔄 Uploading: ${percent}%`;

            // === скорость ===
            const now = Date.now();
            const diffTime = (now - lastTime) / 1000; // сек
            const diffLoaded = event.loaded - lastLoaded; // байты

            if (diffTime > 0.3) {
                const speed = diffLoaded / diffTime; // bytes/sec
                const speedMB = (speed / (1024 * 1024)).toFixed(2);

                const remaining = event.total - event.loaded;
                const eta = remaining / speed; // sec
                const etaStr = eta > 1 ? `${eta.toFixed(1)}s` : "<1s";

                speedInfo.innerText = `⚡ ${speedMB} MB/s — ETA: ${etaStr}`;

                lastLoaded = event.loaded;
                lastTime = now;
            }
        }
    };

    xhr.onload = () => {
        if (xhr.status === 200) {
            const resp = JSON.parse(xhr.responseText);
            progressBar.style.width = "100%";
            speedInfo.innerText = "✅ Completed";

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