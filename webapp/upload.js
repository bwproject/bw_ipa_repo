const tg = window.Telegram.WebApp;
const fileInput = document.getElementById("file");
const uploadBtn = document.getElementById("upload");
const statusDiv = document.getElementById("status");

// Подключаем MainButton для удобного интерфейса
tg.MainButton.setText("Upload");
tg.MainButton.show();

uploadBtn.addEventListener("click", async () => {
    const file = fileInput.files[0];
    if (!file) {
        statusDiv.innerText = "❌ Please select a .ipa file";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

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