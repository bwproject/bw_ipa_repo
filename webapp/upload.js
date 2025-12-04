let tg = window.Telegram.WebApp;

document.getElementById("upload").onclick = async () => {
    const file = document.getElementById("file").files[0];
    if (!file) return;

    const form = new FormData();
    form.append("file", file);

    document.getElementById("status").innerText = "Uploading...";

    const res = await fetch("/upload", {
        method: "POST",
        body: form
    });

    const data = await res.json();
    document.getElementById("status").innerText = JSON.stringify(data);
};