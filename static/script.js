
const statusText = document.getElementById("status");
const messages = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");

let socket = null;

// اتصال خودکار به WebSocket
function connectToChat() {
    const protocol =
        window.location.protocol === "https:" ? "wss:" : "ws:";

    socket = new WebSocket(
        `${protocol}//${window.location.host}/ws`
    );

    socket.addEventListener("open", () => {
        statusText.textContent = "اتصال برقرار شد؛ در حال بررسی نشست...";
    });

    // دریافت اطلاعات از سرور
    socket.addEventListener("message", (event) => {
        let data;

        try {
            data = JSON.parse(event.data);
        } catch {
            return;
        }

        if (data.type === "login_success") {
            statusText.textContent = `متصل شدی؛ خوش آمدی ${data.username}`;
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
            return;
        }

        // نمایش پیام دریافتی
        if (data.username && typeof data.message === "string") {
            const item = document.createElement("div");
            item.className = "message";

            const sender = document.createElement("strong");
            sender.textContent = data.username + ": ";

            const content = document.createElement("span");
            content.textContent = data.message;

            item.append(sender, content);
            messages.appendChild(item);

            messages.scrollTop = messages.scrollHeight;
        }
    });

    // مدیریت قطع اتصال
    socket.addEventListener("close", () => {
        statusText.textContent =
            "اتصال قطع شد؛ اگر وارد حساب نشده‌ای، دوباره وارد شو.";

        messageInput.disabled = true;
        sendButton.disabled = true;
    });

    socket.addEventListener("error", () => {
        statusText.textContent = "خطا در ارتباط با سرور.";
    });
}

// ارسال پیام
chatForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const message = messageInput.value.trim();

    if (!socket || socket.readyState !== WebSocket.OPEN) {
        statusText.textContent = "اتصال برقرار نیست.";
        return;
    }

    if (!message) return;

    socket.send(JSON.stringify({ message }));

    messageInput.value = "";
    messageInput.focus();
});

// شروع اتصال هنگام بارگذاری صفحه
connectToChat();
